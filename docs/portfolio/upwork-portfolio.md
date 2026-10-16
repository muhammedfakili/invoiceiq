# Upwork portfolio entry — InvoiceIQ

Same layout as ScrapePilot and DocuMind: title, role, 5 skills, one paragraph (600-character limit), cover + 5 images.

**Title** (62 characters)
InvoiceIQ — AI Invoice Extraction with Checks and Human Review

**Role**
AI Engineer

**Skills**
Data Extraction · Python · Large Language Model · FastAPI · OCR

**Description** (542 / 600 characters)
Upload invoices (PDFs, scans or phone photos) and get checked data in Excel. An LLM fills a fixed schema, 13 rule checks verify it (totals add up, date order per country, value really on the page), and a reviewer sees only the flagged fields. Tested on 30 synthetic invoices from 6 countries: header accuracy 21.7% with a plain prompt, 100% in two runs with InvoiceIQ; 57/60 invoices fully correct, 0 silent errors. Reading PDF text alone swapped vendor and customer 8 times; adding page images fixed it. FastAPI, Streamlit, Docker, 42 tests.

**Images, in this order**
| File | Shows |
|---|---|
| `00-cover.png` | Cover: black background, robot, "AI INVOICE / EXTRACTION / & REVIEW" (same style as the other covers) |
| `01-photo-extracted.png` | A UK invoice photographed on a table, read straight from the image: every check passed |
| `02-flagged-total.png` | A total that doesn't add up is flagged on subtotal, tax and total, with the reason and the likely fix |
| `03-all-checks.png` | Every rule check that ran on a French invoice (deposit, date 06/08 read as 6 August, grounded in the PDF text) |
| `04-approved-export.png` | Three approved invoices ready for the Excel download |
| `05-measured-results.png` | Header accuracy: plain prompt 21.7% → text-only 96% (8 silent errors) → InvoiceIQ 100% (0 silent errors) |

Every number comes from `eval/results/` (baseline_no_schema, eval_text-pdf, eval_auto, eval_auto-r2).
Images are reproducible: `shots.py` (Playwright against the running app) and `chart.py` in this folder.
Screenshot 02: the wrong total was typed in on purpose to show the check (the model read this invoice correctly).
