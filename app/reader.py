"""Turn an uploaded file into what the LLM can read: text, page images, or both.

Three kinds of input arrive in practice:
  * digital PDF  -- has a text layer (exported from accounting software)
  * scanned PDF  -- only pictures of pages, no text at all
  * photo        -- JPG/PNG from a phone

`read_document` always renders page images (the review screen shows them, and
vision mode reads them) and also pulls the text layer when there is one.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image as PILImage
from PIL import ImageOps

from app.llm import Image

RENDER_DPI = 150  # enough for small print; a page is ~1240x1754 px
MAX_SIDE = 2000  # photos from phones are 4000+ px; the model doesn't need that many
MAX_PAGES = 10
# Fewer characters than this per page means "no real text layer": a scan, or a PDF
# whose only text is a page number.
MIN_TEXT_PER_PAGE = 40

PDF_TYPES = {".pdf"}
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}


class UnsupportedFile(ValueError):
    """Not a PDF or image we can read."""


@dataclass
class Document:
    name: str
    kind: str  # "pdf_text" | "pdf_scan" | "image"
    pages: list[Image] = field(default_factory=list)  # page images, always present
    text: str | None = None  # text layer, only for pdf_text

    @property
    def has_text(self) -> bool:
        return self.text is not None


def read_document(data: bytes, name: str) -> Document:
    suffix = Path(name).suffix.lower()
    if suffix in PDF_TYPES:
        return _read_pdf(data, name)
    if suffix in IMAGE_TYPES:
        return Document(name=name, kind="image", pages=[_normalise_image(data)])
    raise UnsupportedFile(f"Unsupported file type '{suffix}'. Upload a PDF, JPG or PNG.")


def read_path(path: str | Path) -> Document:
    path = Path(path)
    return read_document(path.read_bytes(), path.name)


def _read_pdf(data: bytes, name: str) -> Document:
    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        raise UnsupportedFile(f"Could not open '{name}' as a PDF: {exc}") from exc
    n = min(len(pdf), MAX_PAGES)
    pages = [_png(pdf[i].render(scale=RENDER_DPI / 72).to_pil()) for i in range(n)]

    with pdfplumber.open(io.BytesIO(data)) as plumber:
        texts = [(page.extract_text() or "").strip() for page in plumber.pages[:n]]
    if sum(len(t) for t in texts) >= MIN_TEXT_PER_PAGE * n:
        text = "\n\n".join(f"--- page {i + 1} ---\n{t}" for i, t in enumerate(texts)) if n > 1 else texts[0]
        return Document(name=name, kind="pdf_text", pages=pages, text=text)
    return Document(name=name, kind="pdf_scan", pages=pages)


def _normalise_image(data: bytes) -> Image:
    try:
        img = PILImage.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # PIL raises many different types for broken files
        raise UnsupportedFile(f"Could not read the image: {exc}") from exc
    img = ImageOps.exif_transpose(img).convert("RGB")  # phone photos store rotation in EXIF
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return Image(buf.getvalue(), "image/jpeg")


def _png(img: PILImage.Image) -> Image:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return Image(buf.getvalue(), "image/png")
