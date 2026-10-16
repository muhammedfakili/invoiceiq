"""Score extractions against data/invoices/truth.json, field by field (B6).

Clients don't ask "is it accurate?" -- they ask "how often is the total wrong,
and would I notice?". So we measure two things:

  1. accuracy per field   (vendor 100%, invoice_date 93%, ...)
  2. what validation does with the errors:
       caught       -- wrong AND flagged for review (fine: a human fixes it)
       silent error -- wrong and NOT flagged (the dangerous kind)
       false alarm  -- right but flagged (costs a few seconds of review)

Extractions are cached on disk (eval/cache, gitignored) keyed by file, mode,
model and prompt, so re-scoring never spends API quota twice.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.config import PROJECT_ROOT
from app.extract import SYSTEM_PROMPT, Extraction, Mode, choose_mode, extract
from app.llm import LLMProvider
from app.reader import Document
from app.schema import HEADER_FIELDS, MONEY_FIELDS, Invoice
from app.validate import Review, validate

CACHE_DIR = PROJECT_ROOT / "eval" / "cache"
SCORED_FIELDS = [*HEADER_FIELDS, "line_items"]


def _norm_text(s: object) -> str:
    return re.sub(r"[\W_]+", " ", str(s or "")).strip().casefold()


def field_correct(name: str, got: object, want: object) -> bool:
    if name in MONEY_FIELDS:
        return got is not None and want is not None and abs(float(got) - float(want)) <= 0.01
    if name == "invoice_number":
        return re.sub(r"\s+", "", str(got or "")).casefold() == re.sub(r"\s+", "", str(want or "")).casefold()
    if name in ("invoice_date", "due_date", "currency"):
        return (str(got) if got is not None else None) == (str(want) if want is not None else None)
    if name == "line_items":
        return sorted(round(x["amount"], 2) for x in got) == sorted(round(x["amount"], 2) for x in want)
    return _norm_text(got) == _norm_text(want)


@dataclass
class DocResult:
    id: str
    format: str
    mode: str
    seconds: float
    input_tokens: int
    output_tokens: int
    error: str | None = None
    correct: dict[str, bool] = field(default_factory=dict)
    flagged: dict[str, list[str]] = field(default_factory=dict)
    got: dict = field(default_factory=dict)

    @property
    def wrong(self) -> list[str]:
        return [f for f, ok in self.correct.items() if not ok]

    @property
    def all_correct(self) -> bool:
        return self.error is None and all(self.correct.values())


def score(doc_id: str, truth: dict, ex: Extraction, review: Review | None) -> DocResult:
    r = DocResult(doc_id, truth["format"], ex.mode, ex.seconds, ex.input_tokens, ex.output_tokens, ex.error)
    if ex.invoice is None:
        r.correct = dict.fromkeys(SCORED_FIELDS, False)
        r.flagged = {f: ["extraction failed"] for f in SCORED_FIELDS}
        return r
    got = ex.invoice.model_dump(mode="json")
    r.got = got
    r.correct = {f: field_correct(f, got[f], truth[f]) for f in SCORED_FIELDS}
    r.flagged = review.flags if review else {}
    return r


# --------------------------------------------------------------------------- cache


def _cache_key(path: Path, mode: str, model: str, tag: str = "") -> str:
    h = hashlib.sha256()
    for part in (path.read_bytes(), mode.encode(), model.encode(), tag.encode(), SYSTEM_PROMPT.encode(),
                 json.dumps(Invoice.model_json_schema(), sort_keys=True).encode()):
        h.update(part)
    return h.hexdigest()[:24]


def cached_extract(path: Path, doc: Document, mode: Mode, llm: LLMProvider, tag: str = "") -> Extraction:
    """`tag` forces a fresh run (e.g. "repeat2") to measure run-to-run noise."""
    used = choose_mode(doc, mode)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    file = CACHE_DIR / f"{path.stem}-{used}-{_cache_key(path, used, llm.model, tag)}.json"
    if file.exists():
        data = json.loads(file.read_text(encoding="utf-8"))
        inv = data.pop("invoice")
        return Extraction(invoice=Invoice.model_validate(inv) if inv else None, **data)
    ex = extract(doc, used, llm)
    if ex.error is None:  # don't cache failures (rate limits); retry them next run
        data = asdict(ex)
        data["invoice"] = ex.invoice.model_dump(mode="json") if ex.invoice else None
        file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return ex


# --------------------------------------------------------------------------- summaries


def pct(n: int, d: int) -> str:
    return f"{n / d:.0%}" if d else "–"


def summarise(results: list[DocResult]) -> dict:
    n = len(results)
    wrong = [(r, f) for r in results for f in r.wrong]
    caught = [(r, f) for r, f in wrong if f in r.flagged]
    flagged = [(r, f) for r in results for f in r.flagged if f in SCORED_FIELDS]
    false_alarms = [(r, f) for r, f in flagged if r.correct.get(f, True)]
    no_flags = [r for r in results if not r.flagged]
    return {
        "docs": n,
        "field_accuracy": {f: sum(r.correct[f] for r in results) / n for f in SCORED_FIELDS} if n else {},
        "header_accuracy": (sum(r.correct[f] for r in results for f in HEADER_FIELDS) / (n * len(HEADER_FIELDS))
                            if n else 0),
        "docs_all_correct": sum(r.all_correct for r in results),
        "wrong_fields": len(wrong),
        "caught": len(caught),
        "silent_errors": [(r.id, f) for r, f in wrong if f not in r.flagged],
        "false_alarms": len(false_alarms),
        "docs_flagged": n - len(no_flags),
        "straight_through": len(no_flags),
        "straight_through_correct": sum(r.all_correct for r in no_flags),
        "avg_seconds": sum(r.seconds for r in results) / n if n else 0,
        "avg_input_tokens": sum(r.input_tokens for r in results) / n if n else 0,
        "avg_output_tokens": sum(r.output_tokens for r in results) / n if n else 0,
        "errors": [r.id for r in results if r.error],
    }


def run(paths: list[Path], truth: dict, mode: Mode, llm: LLMProvider, progress=print, tag: str = "") -> list[DocResult]:
    from app.reader import read_path

    results = []
    for i, path in enumerate(paths, 1):
        doc = read_path(path)
        ex = cached_extract(path, doc, mode, llm, tag)
        review = validate(ex.invoice, doc) if ex.invoice else None
        r = score(path.stem, truth[path.stem], ex, review)
        results.append(r)
        status = "ok" if r.all_correct else ("ERROR " + str(r.error)[:80] if r.error else "wrong: " + ", ".join(r.wrong))
        progress(f"[{i}/{len(paths)}] {path.name} ({r.mode}, {r.seconds:.1f}s) {status}"
                 + (f" | flagged: {', '.join(r.flagged)}" if r.flagged else ""))
    return results
