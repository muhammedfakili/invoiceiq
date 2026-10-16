"""HTTP API: upload an invoice, get checked fields back; re-check edits; export.

    GET  /health               provider/model, ready or not
    POST /extract              multipart file -> invoice + checks + flags (+ page images)
    POST /validate             edited invoice JSON -> checks + flags (after a human correction)
    POST /export?format=xlsx   approved invoices -> Excel (or csv)
    GET  /samples              names of demo invoices;  GET /samples/{name} -> the file

If APP_API_KEY is set, every route except /health needs header X-API-Key.

Run:  uv run uvicorn app.api:app --port 8000
"""

from __future__ import annotations

import base64
from datetime import date
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.config import DATA_DIR, settings
from app.export import ApprovedInvoice, to_csv, to_excel
from app.extract import extract
from app.llm import ProviderNotConfigured, get_llm
from app.reader import UnsupportedFile, read_document
from app.schema import Invoice
from app.validate import validate

MAX_UPLOAD_MB = 15
SAMPLES_DIR = DATA_DIR / "invoices"
SAMPLE_FILES = ["inv03-us-pdf.pdf", "inv11-de-pdf.pdf", "inv16-fr-pdf.pdf", "inv24-fr-scan.pdf",
                "inv27-uk-photo.jpg", "inv28-de-photo.jpg"]

app = FastAPI(title="InvoiceIQ", version="1.0", description="Invoice extraction with validation and review")


def require_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if settings.api_key_required and x_api_key != settings.app_api_key:
        raise HTTPException(401, "Missing or wrong X-API-Key")


class CheckOut(BaseModel):
    name: str
    ok: bool
    message: str
    fields: list[str]


class ReviewOut(BaseModel):
    checks: list[CheckOut]
    flags: dict[str, list[str]]
    needs_review: bool


class Page(BaseModel):
    mime_type: str
    data_base64: str


class ExtractOut(ReviewOut):
    file: str
    kind: str
    mode: str
    model: str
    seconds: float
    input_tokens: int
    output_tokens: int
    invoice: Invoice
    pages: list[Page] = []


class ValidateIn(BaseModel):
    invoice: Invoice


class ApprovedIn(BaseModel):
    file: str
    invoice: Invoice
    corrected_fields: list[str] = []
    reviewed_flags: list[str] = []


def _review_out(review) -> dict:
    return {
        "checks": [CheckOut(name=c.name, ok=c.ok, message=c.message, fields=c.fields) for c in review.checks],
        "flags": review.flags,
        "needs_review": review.needs_review,
    }


@app.get("/health")
def health() -> dict:
    try:
        llm = get_llm()
        return {"status": "ok", "provider": llm.name, "model": llm.model}
    except ProviderNotConfigured as exc:
        return {"status": "no_llm_key", "detail": str(exc)}


@app.post("/extract", response_model=ExtractOut, dependencies=[Depends(require_key)])
def extract_invoice(
    file: Annotated[UploadFile, File()],
    mode: Annotated[Literal["auto", "text", "vision", "hybrid"], Query()] = "auto",
    include_pages: Annotated[bool, Query(description="return page images for the review screen")] = True,
) -> ExtractOut:
    # A plain `def` (not async): FastAPI runs it in a worker thread, so a slow LLM call
    # doesn't freeze the server for everyone else.
    data = file.file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {MAX_UPLOAD_MB} MB")
    if not data:
        raise HTTPException(400, "Empty file")
    try:
        doc = read_document(data, file.filename or "upload")
    except UnsupportedFile as exc:
        raise HTTPException(415, str(exc)) from exc
    try:
        llm = get_llm()
    except ProviderNotConfigured as exc:
        raise HTTPException(503, str(exc)) from exc
    ex = extract(doc, mode, llm)
    if ex.invoice is None:
        raise HTTPException(502, f"Extraction failed: {ex.error}")
    pages = [Page(mime_type=p.mime_type, data_base64=base64.b64encode(p.data).decode()) for p in doc.pages]
    return ExtractOut(
        file=doc.name, kind=doc.kind, mode=ex.mode, model=ex.model, seconds=round(ex.seconds, 2),
        input_tokens=ex.input_tokens, output_tokens=ex.output_tokens, invoice=ex.invoice,
        pages=pages if include_pages else [], **_review_out(validate(ex.invoice, doc)),
    )


@app.post("/validate", response_model=ReviewOut, dependencies=[Depends(require_key)])
def validate_invoice(body: ValidateIn) -> ReviewOut:
    # No document here, so the "is it in the text?" check is skipped: a human just typed the value.
    return ReviewOut(**_review_out(validate(body.invoice)))


@app.post("/export", dependencies=[Depends(require_key)])
def export(approved: list[ApprovedIn], format: Annotated[Literal["xlsx", "csv"], Query()] = "xlsx") -> Response:
    if not approved:
        raise HTTPException(400, "Nothing to export")
    items = [ApprovedInvoice(a.file, a.invoice, a.corrected_fields, a.reviewed_flags) for a in approved]
    stamp = date.today().isoformat()
    if format == "csv":
        return Response(to_csv(items), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="invoices-{stamp}.csv"'})
    return Response(
        to_excel(items),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="invoices-{stamp}.xlsx"'},
    )


@app.get("/samples", dependencies=[Depends(require_key)])
def samples() -> list[str]:
    return [f for f in SAMPLE_FILES if (SAMPLES_DIR / f).exists()]


@app.get("/samples/{name}", dependencies=[Depends(require_key)])
def sample(name: str) -> FileResponse:
    if name not in SAMPLE_FILES or not (SAMPLES_DIR / name).exists():
        raise HTTPException(404, "No such sample")
    return FileResponse(SAMPLES_DIR / name)
