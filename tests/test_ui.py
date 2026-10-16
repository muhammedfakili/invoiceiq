"""The review screen, driven headless with Streamlit's AppTest against a fake API."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

import ui.client
from app.validate import validate
from tests.conftest import make_invoice

NAMES = ["a-us.pdf", "b-de.pdf", "c-fr.jpg"]


class FakeApi:
    def __init__(self, *args, **kwargs) -> None:
        self.exported: list = []

    def health(self) -> dict:
        return {"status": "ok", "model": "fake"}

    def samples(self) -> list[str]:
        return NAMES

    def sample(self, name: str) -> bytes:
        return name.encode()

    def extract(self, name: str, data: bytes) -> dict:
        inv = make_invoice(invoice_number=f"N-{name}")
        review = validate(inv)
        return {"file": name, "kind": "pdf_text", "mode": "hybrid", "model": "fake", "seconds": 1.0,
                "input_tokens": 10, "output_tokens": 5, "invoice": inv.model_dump(mode="json"), "pages": [],
                "checks": [c.__dict__ for c in review.checks], "flags": review.flags,
                "needs_review": review.needs_review}

    def validate(self, invoice: dict) -> dict:
        from app.schema import Invoice

        review = validate(Invoice.model_validate(invoice))
        return {"checks": [c.__dict__ for c in review.checks], "flags": review.flags,
                "needs_review": review.needs_review}

    def export(self, approved: list[dict], fmt: str = "xlsx") -> bytes:
        self.exported = approved
        return b"PK"


@pytest.fixture
def at(monkeypatch) -> AppTest:
    monkeypatch.setattr(ui.client, "ApiClient", FakeApi)
    app = AppTest.from_file("../ui/app.py", default_timeout=30)
    app.run()
    next(b for b in app.sidebar.button if "sample" in b.label).click().run()
    return app


def button(at: AppTest, text: str):
    return next(b for b in at.button if text in b.label)


def test_samples_load_clean(at):
    assert not at.exception
    assert list(at.session_state["docs"]) == NAMES
    assert all(d["status"] == "ready" for d in at.session_state["docs"].values())


def test_wrong_total_is_flagged_and_approve_hits_the_selected_invoice(at):
    at.selectbox(key="selected").set_value("b-de.pdf").run()
    at.number_input(key="b-de.pdf-total").set_value(999.0)
    button(at, "re-check").click().run()

    docs = at.session_state["docs"]
    assert docs["b-de.pdf"]["status"] == "needs review"
    assert "total" in docs["b-de.pdf"]["flags"]
    assert at.selectbox(key="selected").value == "b-de.pdf"  # the bug: this used to jump to a-us.pdf
    assert button(at, "Approve").disabled  # flagged fields must be confirmed first

    at.checkbox(key="b-de.pdf-confirm").check().run()
    button(at, "Approve").click().run()
    docs = at.session_state["docs"]
    assert docs["b-de.pdf"]["status"] == "approved"
    assert docs["a-us.pdf"]["status"] == "ready"


def test_fixing_the_value_clears_the_flag(at):
    at.selectbox(key="selected").set_value("c-fr.jpg").run()
    at.number_input(key="c-fr.jpg-total").set_value(999.0)
    button(at, "re-check").click().run()
    at.number_input(key="c-fr.jpg-total").set_value(1353.13)
    button(at, "re-check").click().run()
    assert at.session_state["docs"]["c-fr.jpg"]["status"] == "ready"
