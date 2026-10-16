import pytest
from fastapi.testclient import TestClient

from app import api
from app.config import settings
from tests.conftest import INVOICES, FakeLLM, make_invoice


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "get_llm", lambda: FakeLLM(make_invoice().model_dump_json()))
    monkeypatch.setattr(settings, "app_api_key", None)
    return TestClient(api.app)


def upload(client, name, **params):
    path = INVOICES / name
    return client.post("/extract", files={"file": (name, path.read_bytes())}, params=params)


def test_extract_returns_invoice_checks_and_pages(client):
    r = upload(client, "inv01-us-pdf.pdf")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["invoice"]["invoice_number"] == "INV-1042"
    assert body["mode"] == "hybrid" and body["kind"] == "pdf_text" and len(body["pages"]) == 1
    # The fake answer is not this PDF's content, so grounding must flag it.
    assert body["needs_review"] and "invoice_number" in body["flags"]


def test_extract_without_pages(client):
    assert upload(client, "inv27-uk-photo.jpg", include_pages=False).json()["pages"] == []


def test_unsupported_and_empty(client):
    assert client.post("/extract", files={"file": ("a.txt", b"hi")}).status_code == 415
    assert client.post("/extract", files={"file": ("a.pdf", b"")}).status_code == 400


def test_llm_failure_is_502(monkeypatch, client):
    monkeypatch.setattr(api, "get_llm", lambda: FakeLLM("{}", "{}"))
    assert upload(client, "inv01-us-pdf.pdf").status_code == 502


def test_validate_after_human_edit(client):
    inv = make_invoice(total=999.0).model_dump(mode="json")
    body = client.post("/validate", json={"invoice": inv}).json()
    assert body["needs_review"] and "total" in body["flags"]


def test_export_xlsx_and_csv(client):
    item = {"file": "a.pdf", "invoice": make_invoice().model_dump(mode="json"), "corrected_fields": ["total"]}
    r = client.post("/export", json=[item])
    assert r.status_code == 200 and r.content[:2] == b"PK"  # xlsx is a zip
    assert "INV-1042" in client.post("/export?format=csv", json=[item]).text
    assert client.post("/export", json=[]).status_code == 400


def test_samples(client):
    names = client.get("/samples").json()
    assert "inv27-uk-photo.jpg" in names
    assert client.get(f"/samples/{names[0]}").status_code == 200
    assert client.get("/samples/../.env").status_code == 404


def test_api_key(monkeypatch, client):
    monkeypatch.setattr(settings, "app_api_key", "secret")
    assert client.get("/samples").status_code == 401
    assert client.get("/samples", headers={"X-API-Key": "secret"}).status_code == 200
    assert client.get("/health").status_code == 200
