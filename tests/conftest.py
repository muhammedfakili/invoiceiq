from __future__ import annotations

import json
from datetime import date

import pytest

from app.config import DATA_DIR
from app.llm import LLMAnswer
from app.schema import Invoice

INVOICES = DATA_DIR / "invoices"


def make_invoice(**overrides) -> Invoice:
    base = {
        "vendor_name": "Northwind Office Supply", "vendor_address": "2150 Market Street, Denver",
        "customer_name": "Cedar Ridge Accounting LLC", "invoice_number": "INV-1042",
        "invoice_date_as_printed": "03/04/2026", "invoice_date": date(2026, 3, 4), "due_date": date(2026, 4, 3),
        "currency": "USD", "subtotal": 1250.0, "tax": 103.13, "total": 1353.13, "amount_due": 1353.13,
        "line_items": [
            {"description": "Chairs", "quantity": 5, "unit_price": 200.0, "amount": 1000.0},
            {"description": "Desk mats", "quantity": 5, "unit_price": 50.0, "amount": 250.0},
        ],
    }
    base.update(overrides)
    return Invoice.model_validate(base)


class FakeLLM:
    """Returns canned JSON answers in order and records what it was sent."""

    name = "fake"
    model = "fake-model"

    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.calls: list[dict] = []

    def generate(self, system: str, prompt: str) -> LLMAnswer:
        raise NotImplementedError

    def generate_structured(self, system, prompt, images, schema) -> LLMAnswer:
        self.calls.append({"prompt": prompt, "images": len(images)})
        return LLMAnswer(self.answers.pop(0), self.model, 100, 50)


@pytest.fixture
def invoice() -> Invoice:
    return make_invoice()


@pytest.fixture
def truth() -> dict:
    return json.loads((INVOICES / "truth.json").read_text(encoding="utf-8"))
