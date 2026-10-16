"""B1: build the evaluation set -- 30 fictional invoices with known true values.

Real client invoices are private, so we generate our own. That has one big
advantage: every value is known exactly, so per-field accuracy (B6) is a real
measurement, not a guess.

Variety on purpose, because that is what breaks extractors:
  * 6 countries: US, UK, Germany, Switzerland, France, Netherlands -- each with its
    own labels, date order (03/04 = March 4 in the US, 3 April in the UK), number
    format (1,234.50 / 1.234,50 / 1 234,50 / 1'234.50) and tax name.
  * 4 layouts: classic, coloured band, customer-name-first, multi-page (totals on page 2).
  * Traps: deposits (amount due < total), discounts, shipping, two VAT rates,
    reverse charge (0 tax), PO / customer numbers next to the invoice number,
    order and delivery dates next to the invoice date.
  * 3 formats: 20 digital PDFs (text layer), 5 scans (image-only PDF: grey, tilted,
    noisy) and 5 phone photos (JPG: perspective, shadow, blur, table background).

Usage (from the project root):  uv run python -m scripts.b1_dataset
Output: data/invoices/*.pdf|jpg + data/invoices/truth.json
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pypdfium2 as pdfium
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from app.config import DATA_DIR

OUT = DATA_DIR / "invoices"
FONT = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
SEED = 42

# --------------------------------------------------------------------------- locales

LABELS = {
    "en": dict(title="INVOICE", number="Invoice No.", date="Invoice Date", due="Due Date", bill_to="Bill To",
               desc="Description", qty="Qty", price="Unit Price", amount="Amount", subtotal="Subtotal",
               shipping="Shipping", discount="Discount", tax="Tax ({r}%)", total="Total",
               deposit="Deposit received", amount_due="Balance Due", po="PO Number", order_date="Order Date",
               customer_no="Customer ID", page="Page", reverse="Reverse charge: VAT to be accounted for by the "
               "recipient.", continued="continued on next page"),
    "de": dict(title="RECHNUNG", number="Rechnungsnummer", date="Rechnungsdatum", due="Fällig am",
               bill_to="Rechnungsempfänger", desc="Bezeichnung", qty="Menge", price="Einzelpreis",
               amount="Gesamt", subtotal="Nettobetrag", shipping="Versandkosten", discount="Rabatt",
               tax="zzgl. {r} % MwSt.", total="Rechnungsbetrag", deposit="abzgl. Anzahlung",
               amount_due="Zahlbetrag", po="Ihre Bestellnr.", order_date="Lieferdatum", customer_no="Kundennr.",
               page="Seite", reverse="Steuerschuldnerschaft des Leistungsempfängers (Reverse Charge).",
               continued="Fortsetzung auf der nächsten Seite"),
    "fr": dict(title="FACTURE", number="N° de facture", date="Date de facture", due="Échéance",
               bill_to="Facturé à", desc="Désignation", qty="Qté", price="Prix unit. HT", amount="Montant HT",
               subtotal="Total HT", shipping="Frais de port", discount="Remise", tax="TVA {r} %",
               total="Total TTC", deposit="Acompte versé", amount_due="Net à payer", po="Votre commande",
               order_date="Date de livraison", customer_no="Code client", page="Page",
               reverse="Autoliquidation : TVA due par le preneur.", continued="suite page suivante"),
    "nl": dict(title="FACTUUR", number="Factuurnummer", date="Factuurdatum", due="Vervaldatum",
               bill_to="Factuur aan", desc="Omschrijving", qty="Aantal", price="Prijs", amount="Bedrag",
               subtotal="Subtotaal", shipping="Verzendkosten", discount="Korting", tax="BTW {r}%",
               total="Totaal", deposit="Reeds betaald", amount_due="Te betalen", po="Uw referentie",
               order_date="Leverdatum", customer_no="Klantnummer", page="Pagina",
               reverse="BTW verlegd.", continued="vervolg op volgende pagina"),
}
LABELS["uk"] = {**LABELS["en"], "title": "TAX INVOICE", "tax": "VAT @ {r}%", "bill_to": "Invoice To",
                "amount_due": "Amount Payable", "deposit": "Less: payment received", "due": "Payment Due"}
LABELS["us"] = {**LABELS["en"], "tax": "Sales Tax ({r}%)", "number": "Invoice #"}
LABELS["ch"] = {**LABELS["de"], "tax": "MWST {r} %"}

MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
             "October", "November", "December"]


@dataclass(frozen=True)
class Locale:
    code: str
    labels: str
    currency: str
    tax_rates: tuple[float, ...]  # first = standard rate, second = reduced (if any)

    def money(self, x: float) -> str:
        neg, x = x < 0, abs(x)
        s = f"{x:,.2f}"  # 1,234.50
        if self.code == "us":
            out = f"${s}"
        elif self.code == "uk":
            out = f"£{s}"
        elif self.code == "de":
            out = s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        elif self.code == "fr":
            out = s.replace(",", " ").replace(".", ",") + " €"
        elif self.code == "nl":
            out = "€ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
        else:  # ch
            out = "CHF " + s.replace(",", "'")
        return ("-" if neg else "") + out

    def num(self, x: float) -> str:
        """A plain number in the table (no currency symbol)."""
        s = f"{x:,.2f}"
        if self.code in ("de", "nl"):
            return s.replace(",", "X").replace(".", ",").replace("X", ".")
        if self.code == "fr":
            return s.replace(",", " ").replace(".", ",")
        if self.code == "ch":
            return s.replace(",", "'")
        return s

    def day(self, d: date, long: bool) -> str:
        if self.code == "us":
            return f"{MONTHS_EN[d.month - 1]} {d.day}, {d.year}" if long else d.strftime("%m/%d/%Y")
        if self.code == "uk":
            return f"{d.day} {MONTHS_EN[d.month - 1]} {d.year}" if long else d.strftime("%d/%m/%Y")
        if self.code in ("de", "ch"):
            return d.strftime("%d.%m.%Y")
        if self.code == "nl":
            return d.strftime("%d-%m-%Y")
        return d.strftime("%d/%m/%Y")


LOCALES = {
    "us": Locale("us", "us", "USD", (8.25,)),
    "uk": Locale("uk", "uk", "GBP", (20.0, 5.0)),
    "de": Locale("de", "de", "EUR", (19.0, 7.0)),
    "ch": Locale("ch", "ch", "CHF", (8.1, 2.6)),
    "fr": Locale("fr", "fr", "EUR", (20.0, 5.5)),
    "nl": Locale("nl", "nl", "EUR", (21.0, 9.0)),
}

# Fictional companies: (name, address line)
VENDORS = {
    "us": [("Northwind Office Supply", "2150 Market Street, Denver, CO 80205"),
           ("Bluegrass IT Services LLC", "410 W Main St, Lexington, KY 40507"),
           ("Copperline Plumbing & Heating", "77 Industrial Pkwy, Columbus, OH 43215"),
           ("Summit Peak Marketing Inc.", "1800 Broadway Ste 900, Seattle, WA 98122"),
           ("Redwood Catering Co.", "33 Harbor Way, Oakland, CA 94607")],
    "uk": [("Ashford & Lane Ltd", "Unit 7, Riverside Works, Leeds LS11 5QR"),
           ("Kestrel Print Studio Ltd", "14 Mill Lane, Bristol BS1 6QA"),
           ("Fenwick Facilities Management", "2 Station Road, Reading RG1 1LG"),
           ("Thornbury Software Ltd", "88 Deansgate, Manchester M3 2ER")],
    "de": [("Brandt Elektrotechnik GmbH", "Industriestraße 14, 70565 Stuttgart"),
           ("Hoffmann Druck & Medien GmbH", "Am Hafen 9, 28217 Bremen"),
           ("Weber Gebäudereinigung KG", "Lindenallee 52, 50968 Köln"),
           ("Lindqvist Software GmbH", "Torstraße 140, 10119 Berlin")],
    "ch": [("Alpenblick Treuhand AG", "Bahnhofstrasse 21, 8001 Zürich"),
           ("Gerber Holzbau GmbH", "Dorfstrasse 4, 3110 Münsingen")],
    "fr": [("Atelier Moreau SARL", "12 rue des Tanneurs, 69002 Lyon"),
           ("Lumière Événements SAS", "45 avenue Jean Jaurès, 33000 Bordeaux"),
           ("Dubois Informatique", "8 place du Marché, 44000 Nantes")],
    "nl": [("Van Dijk Installatietechniek B.V.", "Kanaalweg 18, 3526 KM Utrecht"),
           ("Bakker Vertaalbureau", "Prinsengracht 512, 1017 KJ Amsterdam")],
}
CUSTOMERS = {
    "us": [("Cedar Ridge Accounting LLC", "88 Pine Ave, Boulder, CO 80302"),
           ("Pinewood Dental Group", "410 Lakeshore Blvd, Duluth, MN 55802"),
           ("Maple Street Bakery", "9 Maple St, Burlington, VT 05401"),
           ("Granite State Logistics", "500 Commerce Dr, Nashua, NH 03063")],
    "uk": [("Moorgate Cafés Ltd", "3 Kirkgate, York YO1 8AA"),
           ("Harrow & Finch Solicitors", "21 Bedford Row, London WC1R 4EB"),
           ("Northgate Veterinary Practice", "6 Northgate, Chester CH1 2HA")],
    "de": [("Kessler Logistik AG", "Hafenweg 3, 20457 Hamburg"),
           ("Praxis Dr. Albers", "Marktplatz 7, 69117 Heidelberg"),
           ("Sonnenhof Hotel GmbH", "Seestraße 30, 82319 Starnberg")],
    "ch": [("Bergmann Immobilien AG", "Limmatquai 70, 8001 Zürich"),
           ("Café Rosengarten", "Gerechtigkeitsgasse 12, 3011 Bern")],
    "fr": [("Boulangerie Petit", "3 rue de la Paix, 75002 Paris"),
           ("Cabinet Lefèvre Avocats", "17 cours Mirabeau, 13100 Aix-en-Provence"),
           ("Hôtel des Arts", "5 rue Sainte-Catherine, 33000 Bordeaux")],
    "nl": [("De Groene Fiets B.V.", "Oudegracht 210, 3511 NR Utrecht"),
           ("Studio Jansen", "Witte de Withstraat 44, 3012 BR Rotterdam")],
}
# (description, unit price range, reduced tax rate applies?)
ITEMS = {
    "en": [("Consulting services (hours)", (85, 180), False), ("Laptop docking station", (120, 260), False),
           ("Monthly software licence", (29, 99), False), ("On-site support visit", (150, 320), False),
           ("Printed brochures (box of 250)", (60, 140), False), ("Network cabling (per metre)", (2, 6), False),
           ("Website maintenance", (200, 600), False), ("Catering: lunch buffet per person", (18, 35), True),
           ("Office chairs", (140, 290), False), ("Cleaning service (hours)", (25, 45), False),
           ("Training workshop (per seat)", (240, 480), False), ("Books and manuals", (20, 60), True)],
    "de": [("Beratung (Std.)", (90, 160), False), ("Montage und Anschluss (Std.)", (65, 95), False),
           ("LED-Hallenleuchte 150 W", (110, 180), False), ("Druck Flyer A5 (1.000 Stk.)", (80, 160), False),
           ("Unterhaltsreinigung Büro (Std.)", (28, 42), False), ("Fachbücher", (25, 70), True),
           ("Softwarelizenz (Monat)", (39, 120), False), ("Lebensmittel für Bewirtung", (40, 120), True),
           ("Anfahrtspauschale", (35, 60), False), ("Wartungsvertrag (Quartal)", (240, 520), False)],
    "fr": [("Prestation de conseil (heure)", (80, 150), False), ("Location de matériel son", (150, 400), False),
           ("Décoration florale", (60, 220), False), ("Repas traiteur (par personne)", (22, 48), True),
           ("Installation poste de travail", (90, 180), False), ("Maintenance informatique (mois)", (120, 300), False),
           ("Livres et documentation", (15, 50), True), ("Déplacement forfaitaire", (40, 90), False)],
    "nl": [("Installatiewerk (uur)", (55, 85), False), ("Vertaling NL-EN (per woord)", (0.12, 0.2), False),
           ("Materiaal en onderdelen", (40, 250), False), ("Boeken", (20, 60), True),
           ("Voorrijkosten", (35, 55), False), ("Onderhoudscontract (jaar)", (300, 700), False)],
}
ITEMS["us"] = ITEMS["uk"] = ITEMS["en"]
ITEMS["ch"] = ITEMS["de"]

# --------------------------------------------------------------------------- invoice spec


@dataclass
class Spec:
    id: str
    locale: Locale
    layout: str  # classic | band | customer_first | multipage
    fmt: str  # pdf | scan | photo
    vendor: tuple[str, str]
    customer: tuple[str, str]
    number: str
    invoice_date: date
    due_date: date | None
    order_date: date | None
    po: str | None
    customer_no: str | None
    items: list[tuple[str, float, float, float]]  # desc, qty, unit, rate
    discount: float = 0.0  # negative amount
    shipping: float = 0.0
    deposit: float = 0.0
    reverse_charge: bool = False
    long_dates: bool = False
    taxes: dict[float, float] = field(default_factory=dict)

    @property
    def subtotal(self) -> float:
        return round(sum(round(q * u, 2) for _, q, u, _ in self.items) + self.discount + self.shipping, 2)

    def compute_taxes(self) -> None:
        if self.reverse_charge or all(rate == 0 for *_, rate in self.items):
            self.taxes = {}
            return
        base: dict[float, float] = {}
        for _, q, u, rate in self.items:
            base[rate] = base.get(rate, 0) + round(q * u, 2)
        std = self.locale.tax_rates[0]
        # Discount and shipping are taxed at the standard rate.
        base[std] = base.get(std, 0) + self.discount + self.shipping
        self.taxes = {r: round(b * r / 100, 2) for r, b in sorted(base.items(), reverse=True)}

    @property
    def tax(self) -> float:
        return round(sum(self.taxes.values()), 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax, 2)

    def truth(self) -> dict:
        return {
            "file": f"{self.id}.{'jpg' if self.fmt == 'photo' else 'pdf'}",
            "format": self.fmt, "locale": self.locale.code, "layout": self.layout,
            "vendor_name": self.vendor[0], "customer_name": self.customer[0], "invoice_number": self.number,
            "invoice_date": self.invoice_date.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "currency": self.locale.currency, "subtotal": self.subtotal, "tax": self.tax, "total": self.total,
            "amount_due": round(self.total - self.deposit, 2),
            "line_items": [{"description": d, "quantity": q, "unit_price": u, "amount": round(q * u, 2)}
                           for d, q, u, _ in self.items]
            + ([{"description": LABELS[self.locale.labels]["discount"] + " 10%", "quantity": None,
                 "unit_price": None, "amount": self.discount}] if self.discount else []),
            "traps": self.traps(),
        }

    def traps(self) -> list[str]:
        t = []
        if self.invoice_date.day <= 12 and self.locale.code in ("us", "uk", "fr") and not self.long_dates:
            t.append("ambiguous date")
        if self.deposit:
            t.append("deposit")
        if self.discount:
            t.append("discount")
        if self.shipping:
            t.append("shipping")
        if len(self.taxes) > 1:
            t.append("two tax rates")
        if self.reverse_charge:
            t.append("reverse charge")
        if self.layout == "customer_first":
            t.append("customer printed bigger")
        if self.layout == "multipage":
            t.append("multi-page")
        if self.po or self.customer_no:
            t.append("other numbers")
        if self.order_date:
            t.append("other dates")
        return t


def make_specs() -> list[Spec]:
    rng = random.Random(SEED)
    # 30 invoices: (locale, layout, format). Formats: 20 pdf, 5 scan, 5 photo.
    plan = [
        ("us", "classic", "pdf"), ("us", "band", "pdf"), ("us", "customer_first", "pdf"), ("us", "multipage", "pdf"),
        ("uk", "classic", "pdf"), ("uk", "band", "pdf"), ("uk", "customer_first", "pdf"),
        ("de", "classic", "pdf"), ("de", "band", "pdf"), ("de", "multipage", "pdf"), ("de", "customer_first", "pdf"),
        ("ch", "classic", "pdf"), ("ch", "band", "pdf"),
        ("fr", "classic", "pdf"), ("fr", "band", "pdf"), ("fr", "customer_first", "pdf"),
        ("nl", "classic", "pdf"), ("nl", "band", "pdf"), ("uk", "multipage", "pdf"), ("us", "classic", "pdf"),
        ("us", "classic", "scan"), ("uk", "band", "scan"), ("de", "classic", "scan"), ("fr", "band", "scan"),
        ("nl", "customer_first", "scan"),
        ("us", "band", "photo"), ("uk", "classic", "photo"), ("de", "customer_first", "photo"),
        ("ch", "band", "photo"), ("fr", "classic", "photo"),
    ]
    specs = []
    for i, (loc_code, layout, fmt) in enumerate(plan, 1):
        loc = LOCALES[loc_code]
        # Ambiguous dates (day <= 12) on purpose for most invoices.
        d = date(2026, rng.randint(1, 9), rng.randint(1, 12) if rng.random() < 0.7 else rng.randint(13, 28))
        n_items = rng.randint(38, 48) if layout == "multipage" else rng.randint(2, 6)
        catalog = ITEMS[loc_code]
        items = []
        for _ in range(n_items):
            desc, (lo, hi), reduced = rng.choice(catalog)
            qty = float(rng.choice([1, 1, 2, 3, 4, 5, 8, 10, 12, 20])) if hi > 1 else float(rng.randint(800, 2500))
            unit = round(rng.uniform(lo, hi), 2 if hi > 1 else 3)
            if hi > 1:
                unit = round(unit, 0) if rng.random() < 0.5 else round(unit, 2)
            rate = loc.tax_rates[1] if reduced and len(loc.tax_rates) > 1 else loc.tax_rates[0]
            items.append((desc, qty, unit, rate))
        if loc_code == "us":
            items = [(d_, q, u, loc.tax_rates[0]) for d_, q, u, _ in items]
        # A third of US invoices are for services: no sales tax.
        us_no_tax = loc_code == "us" and i % 3 == 0
        gross_items = sum(round(q * u, 2) for _, q, u, _ in items)
        spec = Spec(
            id=f"inv{i:02d}-{loc_code}-{fmt}", locale=loc, layout=layout, fmt=fmt,
            vendor=rng.choice(VENDORS[loc_code]), customer=rng.choice(CUSTOMERS[loc_code]),
            number=_number(rng, loc_code, d),
            invoice_date=d,
            due_date=d + timedelta(days=rng.choice([14, 30, 30, 45])) if rng.random() < 0.8 else None,
            order_date=d - timedelta(days=rng.randint(2, 10)) if rng.random() < 0.45 else None,
            po=f"PO-{rng.randint(10000, 99999)}" if rng.random() < 0.4 else None,
            customer_no=str(rng.randint(10000, 99999)) if rng.random() < 0.35 else None,
            items=items,
            discount=-round(gross_items * 0.1, 2) if rng.random() < 0.25 else 0.0,
            shipping=float(rng.choice([15, 25, 39.9, 49])) if rng.random() < 0.3 else 0.0,
            deposit=round(gross_items * rng.choice([0.3, 0.5]), 0) if rng.random() < 0.25 else 0.0,
            reverse_charge=loc_code in ("de", "nl", "fr") and rng.random() < 0.2,
            long_dates=loc_code in ("us", "uk") and rng.random() < 0.3,
        )
        if us_no_tax:
            spec.items = [(d_, q, u, 0.0) for d_, q, u, _ in spec.items]
        spec.compute_taxes()
        spec.taxes = {r: v for r, v in spec.taxes.items() if r > 0 and v != 0}
        specs.append(spec)
    return specs


def _number(rng: random.Random, loc: str, d: date) -> str:
    n = rng.randint(100, 9999)
    return {
        "us": rng.choice([f"INV-{n}", f"{d.year}-{n:04d}", f"#{n}"]).lstrip("#"),
        "uk": rng.choice([f"AL-{n}", f"INV{d:%y}{n:04d}", f"SI-{n:05d}"]),
        "de": rng.choice([f"RE-{d.year}-{n:04d}", f"R{d:%y}-{n}"]),
        "ch": f"{d.year}.{n:04d}",
        "fr": rng.choice([f"F{d:%y}{n:05d}", f"FA-{d.year}-{n}"]),
        "nl": f"{d.year}{n:05d}",
    }[loc]


# --------------------------------------------------------------------------- PDF drawing


class Doc(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4")
        self.add_font("Arial", "", FONT)
        self.add_font("Arial", "B", FONT_BOLD)
        self.set_auto_page_break(False)

    def t(self, x: float, y: float, s: str, size: float = 10, bold: bool = False, align: str = "L",
          w: float = 0, color: tuple[int, int, int] = (20, 20, 20)) -> None:
        self.set_text_color(*color)
        self.set_font("Arial", "B" if bold else "", size)
        self.set_xy(x, y)
        self.cell(w, 6, s, align=align)


def draw(spec: Spec) -> Doc:
    L = LABELS[spec.locale.labels]
    loc = spec.locale
    doc = Doc()
    doc.add_page()
    accent = random.Random(spec.id).choice([(30, 80, 140), (150, 40, 40), (20, 110, 90), (90, 60, 140)])

    meta = [(L["number"], spec.number), (L["date"], loc.day(spec.invoice_date, spec.long_dates))]
    if spec.order_date:
        meta.append((L["order_date"], loc.day(spec.order_date, spec.long_dates)))
    if spec.due_date:
        meta.append((L["due"], loc.day(spec.due_date, spec.long_dates)))
    if spec.po:
        meta.append((L["po"], spec.po))
    if spec.customer_no:
        meta.append((L["customer_no"], spec.customer_no))

    if spec.layout == "band":
        doc.set_fill_color(*accent)
        doc.rect(0, 0, 210, 32, "F")
        doc.t(15, 8, spec.vendor[0], 16, True, color=(255, 255, 255))
        doc.t(15, 17, spec.vendor[1], 9, color=(235, 235, 235))
        doc.t(140, 10, L["title"], 18, True, "R", 55, color=(255, 255, 255))
        y = 40
        for k, v in meta:
            doc.t(15, y, f"{k}:", 9, True)
            doc.t(55, y, v, 9)
            y += 5.5
        doc.set_draw_color(*accent)
        doc.rect(120, 39, 75, 24)
        doc.t(123, 40, L["bill_to"], 8, True, color=accent)
        doc.t(123, 46, spec.customer[0], 10, True)
        doc.t(123, 52, spec.customer[1], 8)
        y = max(y, 66) + 6
    elif spec.layout == "customer_first":
        # The customer's name is the biggest text on the page; the vendor sits small top-right.
        doc.t(15, 12, L["bill_to"], 8)
        doc.t(15, 18, spec.customer[0].upper(), 19, True)
        doc.t(15, 28, spec.customer[1], 9)
        doc.t(120, 12, spec.vendor[0], 9, True, "R", 75)
        doc.t(120, 17, spec.vendor[1], 7.5, align="R", w=75)
        doc.t(15, 42, L["title"], 13, True, color=accent)
        doc.t(15, 50, "  ·  ".join(f"{k} {v}" for k, v in meta[:3]), 9)
        if len(meta) > 3:
            doc.t(15, 56, "  ·  ".join(f"{k} {v}" for k, v in meta[3:]), 9)
        y = 68
    else:  # classic / multipage
        doc.t(15, 14, spec.vendor[0], 16, True)
        doc.t(15, 22, spec.vendor[1], 9)
        doc.t(140, 14, L["title"], 18, True, "R", 55, color=accent)
        yy = 30
        for k, v in meta:
            doc.t(110, yy, f"{k}:", 9, True, "R", 45)
            doc.t(156, yy, v, 9, align="R", w=39)
            yy += 5.5
        doc.t(15, 38, L["bill_to"] + ":", 9, True)
        doc.t(15, 44, spec.customer[0], 10)
        doc.t(15, 50, spec.customer[1], 9)
        y = max(yy, 58) + 8

    widths = [95, 20, 32, 33]
    header = [L["desc"], L["qty"], L["price"], L["amount"]]
    n_pages = 2 if spec.layout == "multipage" else 1
    page = 1

    def table_header(y: float) -> float:
        doc.set_font("Arial", "B", 9)
        doc.set_text_color(20, 20, 20)
        doc.set_draw_color(120, 120, 120)
        doc.set_xy(15, y)
        for i, (h, w) in enumerate(zip(header, widths)):
            doc.cell(w, 7, h, border="B", align="L" if i == 0 else "R")
        return y + 8

    y = table_header(y)
    doc.set_font("Arial", "", 9)
    for desc, qty, unit, _ in spec.items:
        if y > 262:
            doc.t(15, 270, f"... {L['continued']}", 8, color=(110, 110, 110))
            doc.t(150, 284, f"{L['page']} {page}/{n_pages}", 8, align="R", w=45)
            doc.add_page()
            page += 1
            doc.t(15, 12, f"{spec.vendor[0]} · {L['number']} {spec.number}", 9, color=(90, 90, 90))
            y = table_header(22)
        qty_s = f"{qty:g}" if qty == int(qty) else loc.num(qty)
        unit_s = loc.num(unit) if unit >= 1 else f"{unit:.3f}".replace(".", "," if loc.code in ("de", "nl", "fr") else ".")
        row = [desc, qty_s, unit_s, loc.num(round(qty * unit, 2))]
        doc.set_text_color(20, 20, 20)
        doc.set_font("Arial", "", 9)
        doc.set_xy(15, y)
        for i, (v, w) in enumerate(zip(row, widths)):
            doc.cell(w, 6, v, align="L" if i == 0 else "R")
        y += 6
    if spec.discount:
        doc.set_xy(15, y)
        doc.cell(widths[0], 6, L["discount"] + " 10%")
        doc.cell(sum(widths[1:]), 6, loc.num(spec.discount), align="R")
        y += 6
    doc.line(15, y + 1, 195, y + 1)
    y += 5

    # The printed "Subtotal" excludes shipping; the true net (our `subtotal` field) includes it.
    lines = [(L["subtotal"], loc.money(spec.subtotal - spec.shipping))]
    if spec.shipping:
        lines.append((L["shipping"], loc.money(spec.shipping)))
    for rate, amount in spec.taxes.items():
        lines.append((L["tax"].format(r=f"{rate:g}".replace(".", "," if loc.code in ("de", "fr", "nl") else ".")),
                      loc.money(amount)))
    if spec.locale.code == "us" and not spec.taxes:
        lines.append((L["tax"].format(r="0"), loc.money(0)))
    lines.append((L["total"], loc.money(spec.total)))
    if spec.deposit:
        lines.append((L["deposit"], loc.money(-spec.deposit)))
        lines.append((L["amount_due"], loc.money(spec.total - spec.deposit)))
    for j, (label, value) in enumerate(lines):
        bold = j == len(lines) - 1
        doc.t(95, y, label, 10, bold, "R", 65)
        doc.t(160, y, value, 10, bold, "R", 35)
        y += 6
    if spec.reverse_charge:
        doc.t(15, y + 4, L["reverse"], 8.5, color=(80, 80, 80))
    if spec.layout == "customer_first":
        doc.t(15, 268, f"{spec.vendor[0]} · {spec.vendor[1]}", 8, color=(100, 100, 100))
    if n_pages > 1:
        doc.t(150, 284, f"{L['page']} {page}/{n_pages}", 8, align="R", w=45)
    return doc


# --------------------------------------------------------------------------- scans and photos


def render_pages(pdf_path, dpi: int) -> list[Image.Image]:
    pdf = pdfium.PdfDocument(str(pdf_path))
    return [page.render(scale=dpi / 72).to_pil().convert("RGB") for page in pdf]


def make_scan(img: Image.Image, rng: random.Random) -> Image.Image:
    g = ImageOps.grayscale(img)
    g = g.rotate(rng.uniform(-1.6, 1.6), expand=True, fillcolor=245, resample=Image.BICUBIC)
    arr = np.asarray(g).astype(np.float32)
    arr = arr * 0.85 + 30  # washed-out contrast
    arr += np.random.default_rng(rng.randint(0, 10**6)).normal(0, 9, arr.shape)
    g = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    return g


def make_photo(img: Image.Image, rng: random.Random) -> Image.Image:
    w, h = img.size
    # Paper on a wooden-ish table, seen from a slight angle.
    bg = Image.new("RGB", (int(w * 1.25), int(h * 1.18)), (120, 92, 66))
    draw_bg = ImageDraw.Draw(bg)
    for k in range(0, bg.size[1], 9):
        shade = 110 + rng.randint(-12, 12)
        draw_bg.line([(0, k), (bg.size[0], k + rng.randint(-6, 6))], fill=(shade, int(shade * 0.78), int(shade * 0.55)), width=4)
    ox, oy = int(w * 0.12), int(h * 0.08)
    bg.paste(img, (ox, oy))
    W, H = bg.size
    d = lambda a: int(a * rng.uniform(0.5, 1.0))
    # Perspective: map a slightly skewed quad of the background to the full frame.
    quad = (d(W * 0.06), d(H * 0.03), d(W * 0.02), H - d(H * 0.05), W - d(W * 0.05), H - d(H * 0.02),
            W - d(W * 0.09), d(H * 0.05))
    photo = bg.transform((W, H), Image.QUAD, quad, resample=Image.BICUBIC)
    # Uneven light: a shadow falling from one side.
    arr = np.asarray(photo).astype(np.float32)
    grad = np.linspace(rng.uniform(0.62, 0.75), 1.05, W)[None, :, None]
    arr = arr * grad * np.array([1.0, 0.97, 0.9])  # warm indoor light
    photo = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rng.uniform(0.8, 1.2)))
    return photo.resize((int(W * 0.8), int(H * 0.8)))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()
    rng = random.Random(SEED + 1)
    truth = {}
    for spec in make_specs():
        doc = draw(spec)
        pdf_path = OUT / f"{spec.id}.pdf"
        doc.output(str(pdf_path))
        if spec.fmt == "scan":
            pages = [make_scan(p, rng) for p in render_pages(pdf_path, 150)]
            pages[0].save(pdf_path, save_all=True, append_images=pages[1:], resolution=150)  # image-only PDF
        elif spec.fmt == "photo":
            make_photo(render_pages(pdf_path, 130)[0], rng).save(OUT / f"{spec.id}.jpg", quality=72)
            pdf_path.unlink()
        truth[spec.id] = spec.truth()
    (OUT / "truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False), encoding="utf-8")
    traps: dict[str, int] = {}
    for t in truth.values():
        for trap in t["traps"]:
            traps[trap] = traps.get(trap, 0) + 1
    print(f"Wrote {len(truth)} invoices to {OUT}")
    print("Traps:", ", ".join(f"{k} {v}" for k, v in sorted(traps.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
