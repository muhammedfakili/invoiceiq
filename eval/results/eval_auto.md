# Evaluation: auto

2026-10-16 14:30 · model `gemini-3.5-flash-lite` · mode `auto` · 30 invoices

## Headline

| Metric | Value |
|---|---|
| Header field accuracy (10 fields) | **100.0%** |
| Invoices with every field right (incl. line items) | 28/30 |
| Wrong fields | 2 |
| … caught by validation (flagged) | 2/2 |
| … **silent errors** (wrong, not flagged) | **0** |
| False alarms (right but flagged) | 0 |
| Straight-through (no flags) | 28/30, of which all-correct 28/28 |
| Avg time per invoice | 12.9 s |
| Avg tokens in / out | 1,745 / 670 |

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
| line_items | 93% | 90% | 100% | 100% |

## Errors

| Invoice | Field | Extracted | Truth | Flagged? |
|---|---|---|---|---|
| inv04-us-pdf | line_items | 49 lines, sum 42,644.53 | 48 lines, sum 42,604.63 | yes: looks like a shipping/fee charge, not an item: Shipping |
| inv10-de-pdf | line_items | 49 lines, sum 35,903.36 | 48 lines, sum 35,888.36 | yes: looks like a shipping/fee charge, not an item: Versandkosten |

## False alarms

- none
