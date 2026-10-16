"""B2 baseline: the B0 approach (no schema, "return JSON") scored on all 30 invoices.

Same scorer as eval/run_eval.py, so the numbers are directly comparable. The
naive program looks for our field names at the top level of whatever JSON
comes back -- which is what code consuming an unstructured answer has to do.
Scans and photos get their page images (vision), PDFs their text, as in B0.

Usage (from the project root):  uv run python -m scripts.b2_baseline
"""

from __future__ import annotations

import json
import re
import time

from app.config import DATA_DIR, PROJECT_ROOT
from app.evaluation import SCORED_FIELDS, field_correct
from app.llm import get_llm
from app.reader import read_path

INVOICES = DATA_DIR / "invoices"
CACHE = PROJECT_ROOT / "eval" / "cache" / "baseline"
SYSTEM = "You are an assistant that reads invoices for an accounting team."


def naive_call(llm, doc) -> str:
    """Plain JSON request, no schema. Gemini's generate() has no image input, so use the client directly."""
    from google.genai import types

    prompt = "Extract the data from this invoice. Return JSON."
    contents = [types.Part.from_bytes(data=p.data, mime_type=p.mime_type) for p in doc.pages] + [prompt]
    if doc.text:
        contents = [f"{prompt}\n\n{doc.text}"]
    return llm._call(contents, types.GenerateContentConfig(system_instruction=SYSTEM)).text


def parse(answer: str) -> dict:
    m = re.search(r"\{.*\}", answer, re.DOTALL)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


def main() -> None:
    llm = get_llm()
    truth = json.loads((INVOICES / "truth.json").read_text(encoding="utf-8"))
    CACHE.mkdir(parents=True, exist_ok=True)
    correct = dict.fromkeys(SCORED_FIELDS, 0)
    found = dict.fromkeys(SCORED_FIELDS, 0)
    for doc_id, t in truth.items():
        cache = CACHE / f"{doc_id}.txt"
        if not cache.exists():
            cache.write_text(naive_call(llm, read_path(INVOICES / t["file"])), encoding="utf-8")
            time.sleep(2)
        data = parse(cache.read_text(encoding="utf-8"))
        for f in SCORED_FIELDS:
            if f in data:
                found[f] += 1
                try:
                    correct[f] += field_correct(f, data[f], t[f])
                except (TypeError, ValueError, KeyError):
                    pass
        print(doc_id, "keys:", ", ".join(list(data)[:8]))
    n = len(truth)
    lines = ["# Baseline: no schema (B0 approach) on 30 invoices", "",
             f"Model `{llm.model}`. A program looks for each field name in the returned JSON.", "",
             "| Field | Key present | Usable & correct |", "|---|---|---|"]
    for f in SCORED_FIELDS:
        lines.append(f"| {f} | {found[f]}/{n} | {correct[f]}/{n} |")
    header = [f for f in SCORED_FIELDS if f != "line_items"]
    acc = sum(correct[f] for f in header) / (n * len(header))
    lines += ["", f"**Header field accuracy: {acc:.1%}** (schema version: 100%)"]
    out = PROJECT_ROOT / "eval" / "results" / "baseline_no_schema.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nHeader accuracy without schema: {acc:.1%} -> {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
