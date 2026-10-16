"""Document -> Invoice. The one place that talks to the LLM.

Three modes, measured against each other in B4 (scripts/b4_modes.py):
  text    -- only the PDF's text layer (cheap; impossible for scans and photos)
  vision  -- only the page images (works for everything)
  hybrid  -- text layer + page images together
"auto" picks hybrid when the PDF has text and vision otherwise (the B4 winner).

The model's JSON is checked against the pydantic schema. If it does not fit
(a missing field, "1.234,50" as a string), we send the error back once and let
the model correct itself before giving up.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from app.llm import LLMProvider, get_llm
from app.reader import Document
from app.schema import Invoice

Mode = Literal["auto", "text", "vision", "hybrid"]

SYSTEM_PROMPT = """You extract data from supplier invoices for an accounting system.
Fill every field of the JSON schema from the invoice you are given. Rules:
- Copy names and numbers exactly as printed. Never invent a value; use null for optional fields that are absent.
- Amounts are plain numbers in the invoice currency (1.234,50 -> 1234.5; 1'234.50 -> 1234.5; 1 234,50 -> 1234.5).
- subtotal is the net amount before tax: it includes shipping and fees charged before tax, so subtotal + tax = total.
- Dates: read them in the convention of the invoice's country (US: month first; UK/Europe: day first).
- The vendor issues the invoice and receives the money; the customer is the party billed.
- Read every page. On multi-page invoices the totals are usually on the last page.
- Put a field name in uncertain_fields if the document is unclear about it. Do not guess silently."""


@dataclass
class Extraction:
    invoice: Invoice | None
    mode: str  # the mode actually used
    model: str
    seconds: float
    input_tokens: int = 0
    output_tokens: int = 0
    attempts: int = 1
    error: str | None = None


def choose_mode(doc: Document, mode: Mode) -> str:
    if mode == "auto":
        return "hybrid" if doc.has_text else "vision"
    if mode in ("text", "hybrid") and not doc.has_text:
        return "vision"  # nothing to read as text: a scan or a photo
    return mode


def build_prompt(doc: Document, mode: str) -> tuple[str, list]:
    if mode == "text":
        return f"Invoice text (extracted from the PDF):\n\n{doc.text}", []
    if mode == "hybrid":
        prompt = (
            f"The {len(doc.pages)} image(s) above are the invoice pages. Its text layer, extracted from the PDF, "
            f"is below; use it to get characters exactly right, and the images for layout.\n\n{doc.text}"
        )
        return prompt, doc.pages
    return f"The {len(doc.pages)} image(s) above are the pages of one invoice.", doc.pages


def extract(doc: Document, mode: Mode = "auto", llm: LLMProvider | None = None) -> Extraction:
    llm = llm or get_llm()
    used = choose_mode(doc, mode)
    prompt, images = build_prompt(doc, used)
    start = time.perf_counter()
    tokens_in = tokens_out = 0
    error = None
    for attempt in (1, 2):
        try:
            answer = llm.generate_structured(SYSTEM_PROMPT, prompt, images, Invoice)
        except Exception as exc:  # noqa: BLE001 -- provider errors become a failed extraction, not a crash
            return Extraction(None, used, llm.model, time.perf_counter() - start, tokens_in, tokens_out,
                              attempt, f"{type(exc).__name__}: {exc}")
        tokens_in += answer.input_tokens
        tokens_out += answer.output_tokens
        try:
            invoice = Invoice.model_validate_json(answer.text)
            return Extraction(invoice, used, answer.model, time.perf_counter() - start, tokens_in, tokens_out,
                              attempt)
        except ValidationError as exc:
            error = str(exc)
            prompt = (f"{prompt}\n\nYour previous answer did not match the schema:\n{error}\n"
                      "Return corrected JSON.")
    return Extraction(None, used, llm.model, time.perf_counter() - start, tokens_in, tokens_out, 2, error)
