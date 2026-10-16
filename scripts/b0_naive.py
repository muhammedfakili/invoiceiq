"""B0 experiment: ask the LLM to read invoices with NO schema and NO checks.

Each invoice's text (read with pdfplumber) goes to the model three times:
  1. "plain"  -- "Extract the data from this invoice."
  2. "json"   -- same, plus "Return JSON."  (but we don't say which keys)
  3. "json#2" -- the exact same JSON request again, to see if the keys stay put

Then we try to do what a client's spreadsheet would need: find vendor, date and
total in every answer automatically. Whatever we cannot find, or find wrong, is
the reason B2 (schema), B5 (validation) and B6 (per-field scoring) exist.

Usage (from the project root):  uv run python -m scripts.b0_naive
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime

import pdfplumber

from app.config import DATA_DIR, PROJECT_ROOT
from app.llm import get_llm

SAMPLES = DATA_DIR / "samples"
SYSTEM = "You are an assistant that reads invoices for an accounting team."
PROMPTS = {
    "plain": "Extract the data from this invoice.\n\n{text}",
    "json": "Extract the data from this invoice. Return JSON.\n\n{text}",
}
# Fields a spreadsheet needs, and the key names a program would have to guess.
FIELDS = ["vendor", "invoice_date", "total", "amount_due"]


def read_pdf(path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def parse_json(answer: str) -> dict | None:
    """The model often wraps JSON in ```json fences; strip them and try."""
    m = re.search(r"\{.*\}", answer, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def key_paths(obj, prefix: str = "") -> list[str]:
    """Every key in a nested dict as a dotted path: invoice_details.date, ..."""
    paths = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}{k}"
            paths.append(path)
            paths += key_paths(v, path + ".")
    return paths


def lookup(data: dict, field: str) -> str:
    """What a naive program would do: look for the exact key name at the top level."""
    value = data.get(field)
    return "—" if value is None else str(value)


def main() -> None:
    llm = get_llm()
    truth = json.loads((SAMPLES / "truth.json").read_text(encoding="utf-8"))
    lines = [f"# B0 — No-schema experiment ({llm.name} / {llm.model}, {datetime.now().astimezone():%Y-%m-%d %H:%M})", ""]
    summary = []

    for name, expected in truth.items():
        text = read_pdf(SAMPLES / f"{name}.pdf")
        lines += [f"## {name}.pdf", "", "**True values:** " + ", ".join(f"{k}={v}" for k, v in expected.items()),
                  "", "<details><summary>Text sent to the LLM</summary>", "", "```", text, "```", "", "</details>", ""]
        for label, prompt_key in [("plain", "plain"), ("json", "json"), ("json#2", "json")]:
            answer = llm.generate(SYSTEM, PROMPTS[prompt_key].format(text=text)).text.strip()
            print(f"\n=== {name} [{label}]\n{answer[:600]}")
            lines += [f"### [{label}]", "", answer, ""]
            if prompt_key == "json":
                data = parse_json(answer)
                keys = key_paths(data) if data else []
                found = {f: lookup(data, f) if data else "—" for f in FIELDS}
                summary.append((name, label, data is not None, keys, found))
            time.sleep(4)  # stay under the free tier's per-minute limit

    lines += ["## Summary: keys in the JSON answers", "",
              "| Invoice | Call | JSON parsed | Key count | Top-level keys |", "|---|---|---|---|---|"]
    for name, label, ok, keys, _ in summary:
        top = [k for k in keys if "." not in k]
        lines.append(f"| {name} | {label} | {'yes' if ok else 'NO'} | {len(keys)} | `{', '.join(top)}` |")
    lines += ["", "## Summary: could a program find the keys `vendor`, `invoice_date`, `total`, `amount_due`?", "",
              "| Invoice | Call | " + " | ".join(FIELDS) + " |", "|---|---|" + "---|" * len(FIELDS)]
    for name, label, _, _, found in summary:
        lines.append(f"| {name} | {label} | " + " | ".join(found[f] for f in FIELDS) + " |")

    out = PROJECT_ROOT / "eval" / "results" / "b0_naive.md"
    out.write_text("\n".join(lines), encoding="utf-8-sig")
    print(f"\nSaved to {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
