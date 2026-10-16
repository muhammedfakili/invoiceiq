"""Run the extractor over the 30-invoice set and write a report.

Usage (from the project root):
    uv run python -m eval.run_eval                       # auto mode, all 30 -> eval/results/eval_auto.md
    uv run python -m eval.run_eval --mode vision --only pdf --name vision-pdf
    uv run python -m eval.run_eval --model gemini-3.5-flash --name flash
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from app.config import DATA_DIR, PROJECT_ROOT
from app.evaluation import SCORED_FIELDS, pct, run, summarise
from app.llm import get_llm

INVOICES = DATA_DIR / "invoices"
RESULTS = PROJECT_ROOT / "eval" / "results"
RUNS = PROJECT_ROOT / "eval" / "runs"


def report(name: str, mode: str, model: str, results: list, by_format: dict[str, dict]) -> str:
    s = summarise(results)
    lines = [
        f"# Evaluation: {name}",
        "",
        f"{datetime.now().astimezone():%Y-%m-%d %H:%M} · model `{model}` · mode `{mode}` · {s['docs']} invoices",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Header field accuracy (10 fields) | **{s['header_accuracy']:.1%}** |",
        f"| Invoices with every field right (incl. line items) | {s['docs_all_correct']}/{s['docs']} |",
        f"| Wrong fields | {s['wrong_fields']} |",
        f"| … caught by validation (flagged) | {s['caught']}/{s['wrong_fields']} |",
        f"| … **silent errors** (wrong, not flagged) | **{len(s['silent_errors'])}** |",
        f"| False alarms (right but flagged) | {s['false_alarms']} |",
        (f"| Straight-through (no flags) | {s['straight_through']}/{s['docs']}, of which all-correct "
        f"{s['straight_through_correct']}/{s['straight_through']} |"),
        f"| Avg time per invoice | {s['avg_seconds']:.1f} s |",
        f"| Avg tokens in / out | {s['avg_input_tokens']:,.0f} / {s['avg_output_tokens']:,.0f} |",
        "",
        "## Accuracy per field",
        "",
        "| Field | All | " + " | ".join(by_format) + " |",
        "|---|---|" + "---|" * len(by_format),
    ]
    for f in SCORED_FIELDS:
        cells = [pct(sum(r.correct[f] for r in rs), len(rs)) for rs in by_format.values()]
        lines.append(f"| {f} | {s['field_accuracy'][f]:.0%} | " + " | ".join(cells) + " |")
    lines += ["", "## Errors", "", "| Invoice | Field | Extracted | Truth | Flagged? |", "|---|---|---|---|---|"]
    truth = json.loads((INVOICES / "truth.json").read_text(encoding="utf-8"))
    for r in results:
        for f in r.wrong:
            got = r.got.get(f, "—")
            want = truth[r.id][f]
            if f == "line_items":
                got = f"{len(got)} lines, sum {sum(x['amount'] for x in got):,.2f}" if isinstance(got, list) else got
                want = f"{len(want)} lines, sum {sum(x['amount'] for x in want):,.2f}"
            flag = "yes: " + "; ".join(r.flagged[f]) if f in r.flagged else "**NO**"
            lines.append(f"| {r.id} | {f} | {got} | {want} | {flag} |")
    if not any(r.wrong for r in results):
        lines.append("| – | none | | | |")
    lines += ["", "## False alarms", ""]
    alarms = [(r.id, f, "; ".join(m)) for r in results for f, m in r.flagged.items()
              if f in SCORED_FIELDS and r.correct.get(f, True)]
    lines += [f"- {i} · {f}: {m}" for i, f, m in alarms] or ["- none"]
    if s["errors"]:
        lines += ["", "## Failed extractions", ""] + [f"- {e}" for e in s["errors"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", default="auto", choices=["auto", "text", "vision", "hybrid"])
    p.add_argument("--only", choices=["pdf", "scan", "photo"], help="only one input format")
    p.add_argument("--model", help="override the model (same provider)")
    p.add_argument("--provider", choices=["gemini", "anthropic", "nvidia"])
    p.add_argument("--name", help="report name (default: the mode)")
    p.add_argument("--tag", default="", help="new tag = fresh LLM calls (repeat runs)")
    args = p.parse_args()

    llm = get_llm(args.provider, args.model) if (args.provider or args.model) else get_llm()
    truth = json.loads((INVOICES / "truth.json").read_text(encoding="utf-8"))
    paths = [INVOICES / t["file"] for t in truth.values() if not args.only or t["format"] == args.only]
    name = args.name or args.mode
    results = run(paths, truth, args.mode, llm, tag=args.tag)

    by_format = {}
    for fmt in ("pdf", "scan", "photo"):
        rs = [r for r in results if r.format == fmt]
        if rs:
            by_format[f"{fmt} ({len(rs)})"] = rs
    RESULTS.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"eval_{name}.md"
    out.write_text(report(name, args.mode, llm.model, results, by_format), encoding="utf-8")
    s = summarise(results)
    (RUNS / f"{name}.json").write_text(json.dumps({
        "name": name, "mode": args.mode, "model": llm.model,
        "summary": {k: v for k, v in s.items()},
        "docs": [{"id": r.id, "format": r.format, "mode": r.mode, "seconds": r.seconds, "correct": r.correct,
                  "flagged": r.flagged, "error": r.error} for r in results],
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nHeader accuracy {s['header_accuracy']:.1%} · all-correct {s['docs_all_correct']}/{s['docs']} · "
          f"wrong {s['wrong_fields']} (caught {s['caught']}, silent {len(s['silent_errors'])}) · "
          f"false alarms {s['false_alarms']} · {s['avg_seconds']:.1f} s/invoice")
    print(f"Report: {out.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
