"""The contract: what an extracted invoice looks like.

B0 showed the problem: asked for "JSON", the model invents its own keys every
time (tax / sales_tax, total / gross_amount) and copies dates as printed
(03/04/2026). This model fixes all of that. The LLM is forced to fill exactly
these fields (Gemini's structured output takes the JSON schema below), dates are
real `date`s, amounts are numbers, currency is a 3-letter ISO code.

Field descriptions are part of the prompt: the model reads them, so the rules
for tricky cases (amount due after a deposit, net vs gross) live here.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


class LineItem(BaseModel):
    description: str
    quantity: float | None = Field(None, description="Number of units; null if the line has none (e.g. a discount).")
    unit_price: float | None = Field(None, description="Price per unit as printed; null if not shown.")
    amount: float = Field(description="Line total as printed. Discounts and credits are negative.")


class Invoice(BaseModel):
    vendor_name: str = Field(
        description="The company that ISSUED the invoice and gets paid (seller/supplier). "
        "Not the 'Bill to' / 'Invoice to' / 'Prepared for' customer, even if the customer's name is printed bigger."
    )
    vendor_address: str | None = Field(None, description="The vendor's own address, one line. Null if not printed.")
    customer_name: str = Field(description="The company being billed (Bill to / Invoice to / Kunde / Client).")
    invoice_number: str = Field(
        description="The invoice's own number exactly as printed. Not a PO, order, customer or VAT number."
    )
    invoice_date_as_printed: str = Field(
        description="The invoice date copied character for character as it appears on the page, e.g. '03/04/2026'."
    )
    invoice_date: date = Field(
        description="Issue date of the invoice (not order, delivery or due date). Read the date in the "
        "convention of the invoice's country: US invoices are MM/DD/YYYY, UK and European are DD/MM/YYYY "
        "or DD.MM.YYYY."
    )
    due_date: date | None = Field(None, description="Payment due date if printed as a date; null otherwise.")
    currency: str = Field(description="ISO 4217 code: USD, EUR, GBP, CHF, ... Infer from symbols ($, €, £).")
    subtotal: float = Field(
        description="Net amount before tax (after line discounts). Shipping/fees count if they are listed "
        "before tax is added. Plain number: 1.234,50 is 1234.5."
    )
    tax: float = Field(description="Total tax/VAT/MwSt/TVA amount. 0 if no tax is charged.")
    total: float = Field(description="Invoice total including tax (gross), before any deposit or prior payment.")
    amount_due: float = Field(
        description="What is still to be paid: total minus deposits or payments already received. "
        "Equal to total when nothing was prepaid."
    )
    line_items: list[LineItem] = Field(
        default_factory=list,
        description="Rows of the invoice's item table only (products, services, and discount rows printed in the "
        "table). Shipping, fees, tax and total lines below the table are NOT line items.",
    )
    uncertain_fields: list[str] = Field(
        default_factory=list,
        description="Names of fields above you could not read with confidence (blurry, cut off, ambiguous). "
        "Empty if everything was clear.",
    )

    @field_validator("currency")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()


# The fields we score in the evaluation and show for review, in display order.
HEADER_FIELDS = [
    "vendor_name", "customer_name", "invoice_number", "invoice_date", "due_date",
    "currency", "subtotal", "tax", "total", "amount_due",
]
MONEY_FIELDS = ["subtotal", "tax", "total", "amount_due"]
