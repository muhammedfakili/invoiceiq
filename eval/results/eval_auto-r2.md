# Evaluation: auto-r2

2026-10-16 14:45 · model `gemini-3.5-flash-lite` · mode `auto` · 30 invoices

## Headline

| Metric | Value |
|---|---|
| Header field accuracy (10 fields) | **100.0%** |
| Invoices with every field right (incl. line items) | 29/30 |
| Wrong fields | 1 |
| … caught by validation (flagged) | 1/1 |
| … **silent errors** (wrong, not flagged) | **0** |
| False alarms (right but flagged) | 0 |
| Straight-through (no flags) | 29/30, of which all-correct 29/29 |
| Avg time per invoice | 10.0 s |
| Avg tokens in / out | 1,745 / 671 |

## Accuracy per field

| Field | All | pdf (20) | scan (5) | photo (5) |
|---|---|---|---|---|
| vendor_name | 100% | 100% | 100% | 100% |
| customer_name | 100% | 100% | 100% | 100% |
| invoice_number | 100% | 100% | 100% | 100% |
| invoice_date | 100% | 100% | 100% | 100% |
| due_date | 100% | 100% | 100% | 100% |
| currency | 100% | 100% | 100% | 100% |
| subtotal | 100% | 100% | 100% | 100% |
| tax | 100% | 100% | 100% | 100% |
| total | 100% | 100% | 100% | 100% |
| amount_due | 100% | 100% | 100% | 100% |
| line_items | 97% | 95% | 100% | 100% |

## Errors

| Invoice | Field | Extracted | Truth | Flagged? |
|---|---|---|---|---|
| inv10-de-pdf | line_items | 49 lines, sum 35,903.36 | 48 lines, sum 35,888.36 | yes: looks like a shipping/fee charge, not an item: Versandkosten |

## False alarms

- none
