"""Approved invoices -> an Excel workbook an accountant can open straight away.

Two sheets: "Invoices" (one row per invoice) and "Line items" (one row per
line, keyed by vendor + invoice number). Dates are real Excel dates and amounts
real numbers, so sums and filters work without cleanup.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.schema import Invoice

MONEY = "#,##0.00"
DATE = "yyyy-mm-dd"


@dataclass
class ApprovedInvoice:
    file: str
    invoice: Invoice
    corrected_fields: list[str] = field(default_factory=list)  # what the reviewer changed
    reviewed_flags: list[str] = field(default_factory=list)  # flagged fields a human confirmed


INVOICE_COLUMNS = [
    ("File", 26), ("Vendor", 30), ("Customer", 30), ("Invoice no.", 16), ("Invoice date", 13), ("Due date", 13),
    ("Currency", 9), ("Subtotal", 13), ("Tax", 12), ("Total", 13), ("Amount due", 13),
    ("Corrected by reviewer", 28), ("Flags reviewed", 28),
]
LINE_COLUMNS = [("Vendor", 30), ("Invoice no.", 16), ("Description", 44), ("Quantity", 10),
                ("Unit price", 12), ("Amount", 13), ("Currency", 9)]


def _invoice_row(a: ApprovedInvoice) -> list:
    inv = a.invoice
    return [a.file, inv.vendor_name, inv.customer_name, inv.invoice_number, inv.invoice_date, inv.due_date,
            inv.currency, inv.subtotal, inv.tax, inv.total, inv.amount_due,
            ", ".join(a.corrected_fields), ", ".join(a.reviewed_flags)]


def to_excel(approved: list[ApprovedInvoice]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices"
    _sheet(ws, INVOICE_COLUMNS, [_invoice_row(a) for a in approved], money_cols={8, 9, 10, 11}, date_cols={5, 6})
    lines = wb.create_sheet("Line items")
    rows = [[a.invoice.vendor_name, a.invoice.invoice_number, li.description, li.quantity, li.unit_price,
             li.amount, a.invoice.currency] for a in approved for li in a.invoice.line_items]
    _sheet(lines, LINE_COLUMNS, rows, money_cols={5, 6}, date_cols=set())
    meta = wb.create_sheet("About")
    meta.append(["Exported", datetime.now().strftime("%Y-%m-%d %H:%M")])
    meta.append(["Invoices", len(approved)])
    meta.append(["Source", "InvoiceIQ — extracted by LLM, checked by rules, approved by a reviewer"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _sheet(ws, columns, rows, money_cols: set[int], date_cols: set[int]) -> None:
    header_fill = PatternFill("solid", fgColor="1F3A5F")
    ws.append([name for name, _ in columns])
    for i, (_, width) in enumerate(columns, 1):
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = width
    for row in rows:
        ws.append(row)
    for r in range(2, ws.max_row + 1):
        for c in money_cols:
            ws.cell(row=r, column=c).number_format = MONEY
        for c in date_cols:
            ws.cell(row=r, column=c).number_format = DATE
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions


def to_csv(approved: list[ApprovedInvoice]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([name for name, _ in INVOICE_COLUMNS])
    for a in approved:
        w.writerow([v.isoformat() if hasattr(v, "isoformat") else ("" if v is None else v) for v in _invoice_row(a)])
    return buf.getvalue()
