from datetime import date

from app.reader import Document
from app.validate import numbers_in, validate
from tests.conftest import make_invoice

TODAY = date(2026, 10, 16)


def failed(review) -> set[str]:
    return {c.name for c in review.checks if not c.ok}


def test_clean_invoice_passes(invoice):
    review = validate(invoice, today=TODAY)
    assert not review.needs_review, review.flags


def test_totals_mismatch_flags_money_fields_and_suggests_fix():
    review = validate(make_invoice(subtotal=1200.0), today=TODAY)
    assert "totals" in failed(review)
    assert {"subtotal", "tax", "total"} <= set(review.flags)
    assert "total − tax = 1,250.00" in review.flags["subtotal"][0]


def test_amount_due_above_total_is_flagged():
    assert "amount_due" in validate(make_invoice(amount_due=2000.0), today=TODAY).flags


def test_deposit_is_allowed():
    review = validate(make_invoice(amount_due=853.13), today=TODAY)
    assert "amount_due" not in review.flags


def test_impossible_tax_rate():
    review = validate(make_invoice(tax=500.0, total=1750.0, amount_due=1750.0), today=TODAY)
    assert "tax_rate" in failed(review)


def test_us_date_read_day_first_is_caught():
    # 03/04/2026 on a USD invoice is March 4; the model said 3 April.
    review = validate(make_invoice(invoice_date=date(2026, 4, 3), due_date=None), today=TODAY)
    assert "date_reading" in failed(review)
    assert "invoice_date" in review.flags


def test_european_date_read_month_first_is_caught():
    inv = make_invoice(currency="EUR", invoice_date_as_printed="04.03.2026", invoice_date=date(2026, 4, 3),
                       due_date=None)
    assert "date_reading" in failed(validate(inv, today=TODAY))


def test_written_out_dates_are_not_checked():
    inv = make_invoice(invoice_date_as_printed="March 4, 2026")
    assert "date_reading" not in {c.name for c in validate(inv, today=TODAY).checks}


def test_due_before_invoice_date():
    assert "due_date" in validate(make_invoice(due_date=date(2026, 1, 1)), today=TODAY).flags


def test_vendor_equals_customer():
    review = validate(make_invoice(customer_name="NORTHWIND office supply"), today=TODAY)
    assert {"vendor_name", "customer_name"} <= set(review.flags)


def test_line_items_math_and_sum():
    inv = make_invoice(line_items=[{"description": "Chairs", "quantity": 5, "unit_price": 200.0, "amount": 900.0}])
    assert {"line_items_math", "line_items_sum"} <= failed(validate(inv, today=TODAY))


def test_shipping_gap_between_lines_and_subtotal_is_fine():
    inv = make_invoice(subtotal=1275.0, tax=105.19, total=1380.19, amount_due=1380.19)
    assert "line_items_sum" not in failed(validate(inv, today=TODAY))


def test_shipping_as_line_item_is_flagged():
    items = [{"description": "Chairs", "quantity": 5, "unit_price": 250.0, "amount": 1250.0},
             {"description": "Versandkosten", "quantity": None, "unit_price": None, "amount": 25.0}]
    inv = make_invoice(line_items=items, subtotal=1275.0, tax=105.19, total=1380.19, amount_due=1380.19)
    assert "line_items_charges" in failed(validate(inv, today=TODAY))


def test_model_uncertainty_becomes_a_flag():
    review = validate(make_invoice(uncertain_fields=["total"]), today=TODAY)
    assert "total" in review.flags


def test_grounding_against_pdf_text(invoice):
    text = "NORTHWIND OFFICE SUPPLY\nInvoice # INV-1042\nBill To: Cedar Ridge Accounting LLC\nTOTAL $1,353.13"
    ok = validate(invoice, Document("x.pdf", "pdf_text", text=text), today=TODAY)
    assert "grounded" not in failed(ok)
    bad = validate(make_invoice(invoice_number="INV-1043"), Document("x.pdf", "pdf_text", text=text), today=TODAY)
    assert bad.flags.get("invoice_number") == ["not found in the document text"]


def test_numbers_in_reads_every_locale_format():
    found = numbers_in("$1,234.50 | 1.234,50 € | 1 234,50 € | CHF 1'234.50 | 7,00 | -100.00")
    assert {1234.5, 7.0, 100.0} <= found
