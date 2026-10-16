"""B0: four hand-made sample invoices for the first, schema-free experiment.

Every company here is fictional. Each invoice hides one trap a careless reader
falls into, and the true values (data/samples/truth.json) are chosen so a wrong
reading is visible:

  1. northwind  US invoice, date 03/04/2026 = March 4 (US order), shipping line
  2. brandt     German invoice: German labels, 1.234,50 decimal comma, "MwSt"
  3. harbor     customer name printed big, vendor small; a deposit was already paid,
                so "amount due" is not the total
  4. ashford    UK invoice, 04/03/2026 = 4 March (UK order); three dates on the page
                (order, invoice, due) and a PO number next to the invoice number

Usage (from the project root):  uv run python -m scripts.b0_samples
"""

from __future__ import annotations

import json

from fpdf import FPDF

from app.config import DATA_DIR

OUT = DATA_DIR / "samples"
FONT = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"


def new_pdf() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.add_font("Arial", "", FONT)
    pdf.add_font("Arial", "B", FONT_BOLD)
    pdf.add_page()
    pdf.set_auto_page_break(False)
    return pdf


def text(pdf: FPDF, x: float, y: float, s: str, size: int = 10, bold: bool = False, align: str = "L",
         w: float = 0) -> None:
    pdf.set_font("Arial", "B" if bold else "", size)
    pdf.set_xy(x, y)
    pdf.cell(w, 6, s, align=align)


def table(pdf: FPDF, y: float, header: list[str], rows: list[list[str]], widths: list[float]) -> float:
    """Draw a simple ruled table; returns the y below it."""
    pdf.set_font("Arial", "B", 9)
    pdf.set_xy(15, y)
    for h, w in zip(header, widths):
        pdf.cell(w, 7, h, border="B", align="L" if h == header[0] else "R")
    y += 8
    pdf.set_font("Arial", "", 9)
    for row in rows:
        pdf.set_xy(15, y)
        for i, (v, w) in enumerate(zip(row, widths)):
            pdf.cell(w, 6, v, align="L" if i == 0 else "R")
        y += 6
    pdf.line(15, y + 1, 15 + sum(widths), y + 1)
    return y + 4


def totals(pdf: FPDF, y: float, lines: list[tuple[str, str]], bold_last: bool = True) -> None:
    for i, (label, value) in enumerate(lines):
        bold = bold_last and i == len(lines) - 1
        text(pdf, 110, y, label, 10, bold, "R", 55)
        text(pdf, 165, y, value, 10, bold, "R", 30)
        y += 6


def northwind() -> dict:
    pdf = new_pdf()
    text(pdf, 15, 15, "NORTHWIND OFFICE SUPPLY", 18, True)
    text(pdf, 15, 24, "2150 Market Street, Denver, CO 80205  |  billing@northwind-supply.example")
    text(pdf, 150, 15, "INVOICE", 18, True, "R", 45)
    text(pdf, 120, 32, "Invoice #: INV-1042", align="R", w=75)
    text(pdf, 120, 38, "Date: 03/04/2026", align="R", w=75)
    text(pdf, 120, 44, "Terms: Net 30", align="R", w=75)
    text(pdf, 15, 40, "Bill To:", bold=True)
    text(pdf, 15, 46, "Cedar Ridge Accounting LLC")
    text(pdf, 15, 52, "88 Pine Ave, Boulder, CO 80302")
    y = table(pdf, 66, ["Description", "Qty", "Unit Price", "Amount"], [
        ["Ergonomic office chair", "5", "189.00", "945.00"],
        ["Standing desk mat", "5", "45.00", "225.00"],
        ["Printer paper, case of 10 reams", "2", "40.00", "80.00"],
    ], [100, 20, 30, 30])
    totals(pdf, y, [("Subtotal", "1,250.00"), ("Shipping", "25.00"), ("Sales Tax (8%)", "102.00"),
                    ("TOTAL (USD)", "$1,377.00")])
    text(pdf, 15, 270, "Thank you for your business! Please pay within 30 days.", 9)
    pdf.output(str(OUT / "northwind.pdf"))
    return {"vendor": "Northwind Office Supply", "customer": "Cedar Ridge Accounting LLC",
            "invoice_number": "INV-1042", "invoice_date": "2026-03-04", "currency": "USD",
            "subtotal": 1250.00, "tax": 102.00, "total": 1377.00, "amount_due": 1377.00}


def brandt() -> dict:
    pdf = new_pdf()
    text(pdf, 15, 15, "Brandt Elektrotechnik GmbH", 16, True)
    text(pdf, 15, 23, "Industriestraße 14 · 70565 Stuttgart · USt-IdNr. DE 287 445 190", 9)
    text(pdf, 15, 40, "Kessler Logistik AG")
    text(pdf, 15, 46, "Hafenweg 3")
    text(pdf, 15, 52, "20457 Hamburg")
    text(pdf, 15, 66, "RECHNUNG", 16, True)
    text(pdf, 120, 40, "Rechnungsnummer: RE-2026-0318", align="R", w=75)
    text(pdf, 120, 46, "Rechnungsdatum: 12.03.2026", align="R", w=75)
    text(pdf, 120, 52, "Lieferdatum: 09.03.2026", align="R", w=75)
    text(pdf, 120, 58, "Kundennummer: 40711", align="R", w=75)
    y = table(pdf, 78, ["Bezeichnung", "Menge", "Einzelpreis", "Gesamt"], [
        ["LED-Hallenleuchte 150 W", "6", "142,50 €", "855,00 €"],
        ["Montage und Anschluss (Std.)", "4", "82,00 €", "328,00 €"],
        ["Anfahrtspauschale", "1", "51,50 €", "51,50 €"],
    ], [100, 20, 30, 30])
    totals(pdf, y, [("Nettobetrag", "1.234,50 €"), ("zzgl. 19 % MwSt.", "234,56 €"),
                    ("Rechnungsbetrag", "1.469,06 €")])
    text(pdf, 15, 250, "Zahlbar innerhalb von 14 Tagen ohne Abzug.", 9)
    text(pdf, 15, 256, "IBAN: DE44 6005 0101 0004 2871 33 · BIC: SOLADEST600", 9)
    pdf.output(str(OUT / "brandt.pdf"))
    return {"vendor": "Brandt Elektrotechnik GmbH", "customer": "Kessler Logistik AG",
            "invoice_number": "RE-2026-0318", "invoice_date": "2026-03-12", "currency": "EUR",
            "subtotal": 1234.50, "tax": 234.56, "total": 1469.06, "amount_due": 1469.06}


def harbor() -> dict:
    pdf = new_pdf()
    # The customer's name is the biggest thing on the page; the vendor is small.
    text(pdf, 15, 15, "Prepared for", 9)
    text(pdf, 15, 21, "PINEWOOD DENTAL GROUP", 20, True)
    text(pdf, 15, 31, "410 Lakeshore Blvd, Suite 200, Duluth, MN 55802", 9)
    text(pdf, 130, 15, "Harbor Creative Studio", 10, True, "R", 65)
    text(pdf, 130, 21, "12 Canal St, Duluth, MN 55802", 8, align="R", w=65)
    text(pdf, 130, 26, "hello@harborcreative.example", 8, align="R", w=65)
    text(pdf, 15, 46, "Invoice HCS-2026-019  ·  Issued May 7, 2026  ·  Due June 6, 2026", 10)
    y = table(pdf, 60, ["Service", "Hours", "Rate", "Amount"], [
        ["Brand refresh: logo and colour system", "16", "95.00", "1,520.00"],
        ["Website landing page design", "8", "95.00", "760.00"],
        ["Stock photography licence", "1", "120.00", "120.00"],
    ], [100, 20, 30, 30])
    totals(pdf, y, [("Total", "$2,400.00"), ("Deposit received (Apr 2)", "-$800.00"),
                    ("Balance due", "$1,600.00")])
    text(pdf, 15, y + 30, "Services are not subject to sales tax in this engagement.", 9)
    pdf.output(str(OUT / "harbor.pdf"))
    return {"vendor": "Harbor Creative Studio", "customer": "Pinewood Dental Group",
            "invoice_number": "HCS-2026-019", "invoice_date": "2026-05-07", "currency": "USD",
            "subtotal": 2400.00, "tax": 0.00, "total": 2400.00, "amount_due": 1600.00}


def ashford() -> dict:
    pdf = new_pdf()
    text(pdf, 15, 15, "Ashford & Lane Ltd", 16, True)
    text(pdf, 15, 23, "Unit 7, Riverside Works, Leeds LS11 5QR  ·  VAT Reg. GB 318 2204 57", 9)
    text(pdf, 150, 15, "TAX INVOICE", 14, True, "R", 45)
    text(pdf, 15, 40, "Invoice to:", bold=True)
    text(pdf, 15, 46, "Moorgate Cafés Ltd")
    text(pdf, 15, 52, "3 Kirkgate, York YO1 8AA")
    text(pdf, 110, 40, "Invoice No:", bold=True)
    text(pdf, 150, 40, "AL-7781")
    text(pdf, 110, 46, "Your PO:", bold=True)
    text(pdf, 150, 46, "PO-55120")
    text(pdf, 110, 52, "Order date:", bold=True)
    text(pdf, 150, 52, "28/02/2026")
    text(pdf, 110, 58, "Invoice date:", bold=True)
    text(pdf, 150, 58, "04/03/2026")
    text(pdf, 110, 64, "Payment due:", bold=True)
    text(pdf, 150, 64, "03/04/2026")
    y = table(pdf, 78, ["Item", "Qty", "Unit £", "Net £"], [
        ["Espresso machine descaling service", "4", "150.00", "600.00"],
        ["Grinder burr replacement", "4", "100.00", "400.00"],
        ["Loyalty discount 10%", "", "", "-100.00"],
    ], [100, 20, 30, 30])
    totals(pdf, y, [("Net total", "£900.00"), ("VAT @ 20%", "£180.00"), ("Amount payable", "£1,080.00")])
    pdf.output(str(OUT / "ashford.pdf"))
    return {"vendor": "Ashford & Lane Ltd", "customer": "Moorgate Cafés Ltd",
            "invoice_number": "AL-7781", "invoice_date": "2026-03-04", "currency": "GBP",
            "subtotal": 900.00, "tax": 180.00, "total": 1080.00, "amount_due": 1080.00}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    truth = {"northwind": northwind(), "brandt": brandt(), "harbor": harbor(), "ashford": ashford()}
    (OUT / "truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(truth)} invoices + truth.json to {OUT}")


if __name__ == "__main__":
    main()
