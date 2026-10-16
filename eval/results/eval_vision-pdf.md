# Evaluation: vision-pdf

2026-10-16 14:36 · model `gemini-3.5-flash-lite` · mode `vision` · 20 invoices

## Headline

| Metric | Value |
|---|---|
| Header field accuracy (10 fields) | **100.0%** |
| Invoices with every field right (incl. line items) | 20/20 |
| Wrong fields | 0 |
| … caught by validation (flagged) | 0/0 |
| … **silent errors** (wrong, not flagged) | **0** |
| False alarms (right but flagged) | 0 |
| Straight-through (no flags) | 20/20, of which all-correct 20/20 |
| Avg time per invoice | 12.1 s |
| Avg tokens in / out | 1,507 / 781 |

## Accuracy per field

| Field | All | pdf (20) |
|---|---|---|
| vendor_name | 100% | 100% |
| customer_name | 100% | 100% |
| invoice_number | 100% | 100% |
| invoice_date | 100% | 100% |
| due_date | 100% | 100% |
| currency | 100% | 100% |
| subtotal | 100% | 100% |
| tax | 100% | 100% |
| total | 100% | 100% |
| amount_due | 100% | 100% |
| line_items | 100% | 100% |

## Errors

| Invoice | Field | Extracted | Truth | Flagged? |
|---|---|---|---|---|
| – | none | | | |

## False alarms

- none
