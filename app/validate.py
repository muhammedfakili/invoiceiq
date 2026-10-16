"""Check an extracted invoice with plain code, and flag what a human should look at.

The LLM is good but not perfect, and its mistakes look exactly like correct
answers. These checks need no AI: arithmetic, calendars, and "is this value
actually in the document?". Every failed check flags the fields involved; the
review screen highlights them and the export refuses unreviewed flags.

B6 measures how well this works: of the fields the model got wrong, how many
did we flag (catch rate), and how many flags were false alarms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.reader import Document
from app.schema import HEADER_FIELDS, Invoice

MONEY_TOLERANCE = 0.02  # rounding on printed invoices
MAX_TAX_RATE = 0.27  # highest standard VAT rate in Europe (Hungary)
KNOWN_CURRENCIES = {
    "USD", "EUR", "GBP", "CHF", "CAD", "AUD", "NZD", "JPY", "CNY", "INR", "SEK", "NOK", "DKK", "PLN", "CZK",
    "HUF", "RON", "TRY", "MXN", "BRL", "ZAR", "SGD", "HKD", "AED", "SAR", "ILS", "KRW",
}
# Countries that print the month first. Everyone else in our market prints the day first.
MONTH_FIRST_CURRENCIES = {"USD"}


@dataclass
class Check:
    name: str
    ok: bool
    message: str
    fields: list[str] = field(default_factory=list)


@dataclass
class Review:
    checks: list[Check]

    @property
    def flags(self) -> dict[str, list[str]]:
        """field -> reasons it needs a human look."""
        out: dict[str, list[str]] = {}
        for check in self.checks:
            if not check.ok:
                for f in check.fields:
                    out.setdefault(f, []).append(check.message)
        return out

    @property
    def needs_review(self) -> bool:
        return any(not c.ok for c in self.checks)


def validate(inv: Invoice, doc: Document | None = None, today: date | None = None) -> Review:
    today = today or date.today()
    checks = [
        _totals(inv),
        _amount_due(inv),
        _tax_rate(inv),
        _line_items_sum(inv),
        _line_items_math(inv),
        _line_items_charges(inv),
        _invoice_date_reading(inv),
        _dates_plausible(inv, today),
        _currency(inv),
        _parties(inv),
        _required(inv),
        _model_uncertain(inv),
    ]
    if doc is not None and doc.text:
        checks.append(_grounded(inv, doc.text))
    return Review([c for c in checks if c is not None])


# --------------------------------------------------------------------------- money


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= MONEY_TOLERANCE


def _totals(inv: Invoice) -> Check:
    expected = round(inv.subtotal + inv.tax, 2)
    if _close(expected, inv.total):
        return Check("totals", True, "subtotal + tax = total")
    return Check("totals", False, f"subtotal + tax = {expected:,.2f}, but total is {inv.total:,.2f} "
                 f"(total − tax = {inv.total - inv.tax:,.2f}: shipping or fees left out of the subtotal?)",
                 ["subtotal", "tax", "total"])


def _amount_due(inv: Invoice) -> Check:
    if inv.amount_due < -MONEY_TOLERANCE or inv.amount_due > inv.total + MONEY_TOLERANCE:
        return Check("amount_due", False, f"amount due {inv.amount_due:,.2f} is outside 0 … total "
                     f"({inv.total:,.2f})", ["amount_due"])
    if not _close(inv.amount_due, inv.total):
        # Legitimate (deposit), but it is the number that gets paid: worth a confirmation.
        return Check("amount_due", True, f"amount due is {inv.total - inv.amount_due:,.2f} less than total "
                     "(deposit or prior payment)")
    return Check("amount_due", True, "amount due = total")


def _tax_rate(inv: Invoice) -> Check:
    if inv.subtotal <= 0:
        return Check("tax_rate", True, "no subtotal to compare")
    rate = inv.tax / inv.subtotal
    if rate < 0 or rate > MAX_TAX_RATE:
        return Check("tax_rate", False, f"tax is {rate:.0%} of subtotal; no VAT/sales tax is that high",
                     ["tax", "subtotal"])
    return Check("tax_rate", True, f"effective tax rate {rate:.1%}")


def _line_items_sum(inv: Invoice) -> Check | None:
    if not inv.line_items:
        return None
    lines = round(sum(li.amount for li in inv.line_items), 2)
    gap = round(inv.subtotal - lines, 2)
    if abs(gap) <= MONEY_TOLERANCE:
        return Check("line_items_sum", True, "line items add up to the subtotal")
    if 0 < gap <= 0.25 * inv.subtotal:
        # Shipping and fees are part of the net but usually not table lines.
        return Check("line_items_sum", True, f"line items are {gap:,.2f} below subtotal (shipping or fees)")
    return Check("line_items_sum", False, f"line items add up to {lines:,.2f}, subtotal is {inv.subtotal:,.2f}",
                 ["subtotal", "line_items"])


def _line_items_math(inv: Invoice) -> Check | None:
    bad = [
        li.description for li in inv.line_items
        if li.quantity is not None and li.unit_price is not None
        and abs(li.quantity * li.unit_price - li.amount) > max(MONEY_TOLERANCE, abs(li.amount) * 0.005)
    ]
    if not inv.line_items:
        return None
    if bad:
        return Check("line_items_math", False, f"quantity × unit price ≠ amount on {len(bad)} line(s): "
                     + "; ".join(bad[:3]), ["line_items"])
    return Check("line_items_math", True, "every line: quantity × unit price = amount")


# Shipping/fee rows belong in the subtotal, not the item list (accounting books them separately).
_CHARGE_WORDS = re.compile(
    r"\b(shipping|delivery|freight|postage|versand\w*|fracht|frais de port|livraison|verzend\w*|porto)\b",
    re.IGNORECASE,
)


def _line_items_charges(inv: Invoice) -> Check | None:
    charges = [li.description for li in inv.line_items if li.quantity is None and _CHARGE_WORDS.search(li.description)]
    if charges:
        return Check("line_items_charges", False, "looks like a shipping/fee charge, not an item: "
                     + ", ".join(charges), ["line_items"])
    return None


# --------------------------------------------------------------------------- dates

_NUMERIC_DATE = re.compile(r"^\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2}|\d{4})\s*$")


def _invoice_date_reading(inv: Invoice) -> Check | None:
    """Re-read the printed date ourselves and compare with the model's ISO date.

    03/04/2026 is March 4 in the US and 3 April in Europe. The model is told the
    rule; this check makes sure it followed it.
    """
    m = _NUMERIC_DATE.match(inv.invoice_date_as_printed or "")
    if not m:
        return None  # written-out month ("4 June 2026"): no ambiguity to check
    a, b, y = int(m[1]), int(m[2]), int(m[3])
    y = y + 2000 if y < 100 else y
    month_first = inv.currency in MONTH_FIRST_CURRENCIES
    day, month = (b, a) if month_first else (a, b)
    try:
        expected = date(y, month, day)
    except ValueError:
        # Impossible in the expected order (e.g. 13/05 on a US invoice): the convention guess is wrong.
        return Check("date_reading", False, f"'{inv.invoice_date_as_printed}' is not a valid "
                     f"{'month-first' if month_first else 'day-first'} date; check the date order", ["invoice_date"])
    if expected != inv.invoice_date:
        return Check("date_reading", False, f"'{inv.invoice_date_as_printed}' reads as {expected:%d %b %Y} on a "
                     f"{inv.currency} invoice, extracted {inv.invoice_date:%d %b %Y}", ["invoice_date"])
    return Check("date_reading", True, f"'{inv.invoice_date_as_printed}' read as {expected:%d %b %Y}")


def _dates_plausible(inv: Invoice, today: date) -> Check:
    if not date(2000, 1, 1) <= inv.invoice_date <= today + timedelta(days=60):
        return Check("dates", False, f"invoice date {inv.invoice_date} is implausible", ["invoice_date"])
    if inv.due_date and inv.due_date < inv.invoice_date:
        return Check("dates", False, f"due date {inv.due_date} is before invoice date {inv.invoice_date}",
                     ["due_date", "invoice_date"])
    return Check("dates", True, "dates are plausible")


# --------------------------------------------------------------------------- identity


def _currency(inv: Invoice) -> Check:
    if inv.currency not in KNOWN_CURRENCIES:
        return Check("currency", False, f"'{inv.currency}' is not a known currency code", ["currency"])
    return Check("currency", True, inv.currency)


def _norm(s: str) -> str:
    return re.sub(r"[\W_]+", " ", s).strip().casefold()


def _parties(inv: Invoice) -> Check:
    if _norm(inv.vendor_name) == _norm(inv.customer_name):
        return Check("parties", False, "vendor and customer are the same name", ["vendor_name", "customer_name"])
    return Check("parties", True, "vendor and customer differ")


def _required(inv: Invoice) -> Check:
    empty = [f for f in ("vendor_name", "customer_name", "invoice_number") if not str(getattr(inv, f)).strip()]
    if empty:
        return Check("required", False, "missing: " + ", ".join(empty), empty)
    return Check("required", True, "all required fields present")


def _model_uncertain(inv: Invoice) -> Check | None:
    unsure = [f for f in inv.uncertain_fields if f in HEADER_FIELDS or f == "line_items"]
    if unsure:
        return Check("model_uncertain", False, "the model marked this field as unclear", unsure)
    return None


# --------------------------------------------------------------------------- grounding

_NUMBER = re.compile(r"-?\d[\d.,' ]*\d|-?\d")


def numbers_in(text: str) -> set[float]:
    """Every amount printed in the text, whatever the format (1,234.50 / 1.234,50 / 1 234,50 / 1'234.50)."""
    found: set[float] = set()
    for token in _NUMBER.findall(text):
        for piece in {token, *token.split(" ")}:
            value = _parse_amount(piece.strip())
            if value is not None:
                found.add(round(abs(value), 2))
    return found


def _parse_amount(s: str) -> float | None:
    s = s.replace("'", "").replace(" ", "")
    if not s or not s[-1].isdigit():
        return None
    last_dot, last_comma = s.rfind("."), s.rfind(",")
    dec = max(last_dot, last_comma)
    if dec != -1 and len(s) - dec - 1 == 2:  # two digits after the last separator = cents
        whole, cents = s[:dec], s[dec + 1:]
        whole = whole.replace(".", "").replace(",", "")
        s = f"{whole}.{cents}"
    else:
        s = s.replace(".", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _grounded(inv: Invoice, text: str) -> Check:
    """Text PDFs only: the identifying values must literally appear in the document."""
    flat = _norm(text)
    compact = re.sub(r"\s+", "", text).casefold()
    missing = []
    if re.sub(r"\s+", "", inv.invoice_number).casefold() not in compact:
        missing.append("invoice_number")
    for f in ("vendor_name", "customer_name"):
        if _norm(getattr(inv, f)) not in flat:
            missing.append(f)
    if round(inv.total, 2) not in numbers_in(text):
        missing.append("total")
    if missing:
        return Check("grounded", False, "not found in the document text", missing)
    return Check("grounded", True, "number, names and total appear in the document text")
