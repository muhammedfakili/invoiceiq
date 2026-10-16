# Evaluation: hybrid-pdf-r2

2026-10-16 14:43 · model `gemini-3.5-flash-lite` · mode `hybrid` · 20 invoices

## Headline

| Metric | Value |
|---|---|
| Header field accuracy (10 fields) | **100.0%** |
| Invoices with every field right (incl. line items) | 19/20 |
| Wrong fields | 1 |
| … caught by validation (flagged) | 1/1 |
| … **silent errors** (wrong, not flagged) | **0** |
| False alarms (right but flagged) | 0 |
| Straight-through (no flags) | 19/20, of which all-correct 19/19 |
| Avg time per invoice | 10.6 s |
| Avg tokens in / out | 1,953 / 784 |

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
| line_items | 95% | 95% |

## Errors

| Invoice | Field | Extracted | Truth | Flagged? |
|---|---|---|---|---|
| inv10-de-pdf | line_items | 49 lines, sum 35,903.36 | 48 lines, sum 35,888.36 | yes: looks like a shipping/fee charge, not an item: Versandkosten |

## False alarms

- none
