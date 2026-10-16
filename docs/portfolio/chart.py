"""Portfolio image 05: measured results, read from eval/runs/*.json and eval/results/baseline_no_schema.md."""

import json
import re
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "eval" / "runs"
OUT = ROOT / "docs" / "portfolio" / "05-measured-results.png"


def run(name: str) -> dict:
    return json.loads((RUNS / f"{name}.json").read_text(encoding="utf-8"))["summary"]


baseline = float(re.search(r"Header field accuracy: ([\d.]+)%", (ROOT / "eval/results/baseline_no_schema.md")
                           .read_text(encoding="utf-8")).group(1))
text = run("text-pdf")
final = [run("auto"), run("auto-r2")]
final_acc = sum(r["header_accuracy"] for r in final) / 2 * 100
final_docs = sum(r["docs_all_correct"] for r in final)
final_n = sum(r["docs"] for r in final)

labels = ["Plain LLM prompt, no schema\n(30 invoices)", "Schema, PDF text only\n(20 digital PDFs; scans have no text)",
          "InvoiceIQ: schema + page images + checks\n(30 invoices, 2 runs)"]
values = [baseline, text["header_accuracy"] * 100, final_acc]
notes = ["field names change\nbetween calls",
         f"{len(text['silent_errors'])} silent errors:\nvendor and customer\nswapped (layout lost)",
         f"0 silent errors\n0 false alarms\n{final_docs}/{final_n} invoices\nfully correct"]

BG, FG, MUTED = "#0b0d10", "#f2f6fa", "#8fa0b4"
BLUE, GREY = "#2f7fd4", "#5d6b7c"
fig, ax = plt.subplots(figsize=(15.68, 6.98), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
bars = ax.bar(range(3), values, 0.62, color=[GREY, GREY, BLUE])
for bar, v, note in zip(bars, values, notes):
    x = bar.get_x() + bar.get_width() / 2
    ax.text(x, v + 1.5, f"{v:.1f}%".replace(".0%", "%"), ha="center", va="bottom", color=FG, fontsize=22,
            fontweight="bold")
    ax.text(x, max(v - 6, 3), note, ha="center", va="top", color=BG if v > 30 else FG, fontsize=13,
            fontweight="bold")
ax.set_xticks(range(3), labels, color=FG, fontsize=13)
ax.set_ylim(0, 112)
ax.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"], color=MUTED, fontsize=11)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color(MUTED)
fig.suptitle("Header field accuracy on 30 invoices", color=FG, fontsize=22, fontweight="bold", x=0.06,
             ha="left", y=0.95)
fig.text(0.06, 0.865, "10 fields per invoice · 6 countries · digital PDFs, scans and phone photos · "
         "same model in every bar: Gemini 3.5 Flash-Lite (free tier)",
         color=MUTED, fontsize=12, ha="left")
fig.subplots_adjust(top=0.8, bottom=0.14, left=0.06, right=0.98)
fig.savefig(OUT, facecolor=BG)
print("saved", OUT)
