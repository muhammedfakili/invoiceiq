# Evaluation: vision-pdf-r2

2026-10-16 14:40 · model `gemini-3.5-flash-lite` · mode `vision` · 20 invoices

## Headline

| Metric | Value |
|---|---|
| Header field accuracy (10 fields) | **99.5%** |
| Invoices with every field right (incl. line items) | 18/20 |
| Wrong fields | 3 |
| … caught by validation (flagged) | 3/3 |
| … **silent errors** (wrong, not flagged) | **0** |
| False alarms (right but flagged) | 2 |
| Straight-through (no flags) | 18/20, of which all-correct 18/18 |
| Avg time per invoice | 7.2 s |
| Avg tokens in / out | 1,507 / 788 |

## Accuracy per field

| Field | All | pdf (20) |
|---|---|---|
| vendor_name | 100% | 100% |
| customer_name | 100% | 100% |
| invoice_number | 100% | 100% |
| invoice_date | 100% | 100% |
| due_date | 100% | 100% |
| currency | 100% | 100% |
| subtotal | 95% | 95% |
| tax | 100% | 100% |
| total | 100% | 100% |
| amount_due | 100% | 100% |
| line_items | 90% | 90% |

## Errors

| Invoice | Field | Extracted | Truth | Flagged? |
|---|---|---|---|---|
| inv04-us-pdf | line_items | 49 lines, sum 42,644.53 | 48 lines, sum 42,604.63 | yes: looks like a shipping/fee charge, not an item: Shipping |
| inv10-de-pdf | subtotal | 35893.36 | 35903.36 | yes: subtotal + tax = 42,222.65, but total is 42,232.65 (total − tax = 35,903.36: shipping or fees left out of the subtotal?); line items add up to 35,903.36, subtotal is 35,893.36 |
| inv10-de-pdf | line_items | 49 lines, sum 35,903.36 | 48 lines, sum 35,888.36 | yes: line items add up to 35,903.36, subtotal is 35,893.36; looks like a shipping/fee charge, not an item: Versandkosten |

## False alarms

- inv10-de-pdf · tax: subtotal + tax = 42,222.65, but total is 42,232.65 (total − tax = 35,903.36: shipping or fees left out of the subtotal?)
- inv10-de-pdf · total: subtotal + tax = 42,222.65, but total is 42,232.65 (total − tax = 35,903.36: shipping or fees left out of the subtotal?)
