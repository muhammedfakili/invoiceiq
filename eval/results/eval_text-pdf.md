# Evaluation: text-pdf

2026-10-16 14:32 · model `gemini-3.5-flash-lite` · mode `text` · 20 invoices

## Headline

| Metric | Value |
|---|---|
| Header field accuracy (10 fields) | **96.0%** |
| Invoices with every field right (incl. line items) | 14/20 |
| Wrong fields | 10 |
| … caught by validation (flagged) | 2/10 |
| … **silent errors** (wrong, not flagged) | **8** |
| False alarms (right but flagged) | 0 |
| Straight-through (no flags) | 18/20, of which all-correct 14/18 |
| Avg time per invoice | 7.7 s |
| Avg tokens in / out | 666 / 792 |

## Accuracy per field

| Field | All | pdf (20) |
|---|---|---|
| vendor_name | 80% | 80% |
| customer_name | 80% | 80% |
| invoice_number | 100% | 100% |
| invoice_date | 100% | 100% |
| due_date | 100% | 100% |
| currency | 100% | 100% |
| subtotal | 100% | 100% |
| tax | 100% | 100% |
| total | 100% | 100% |
| amount_due | 100% | 100% |
| line_items | 90% | 90% |

## Errors

| Invoice | Field | Extracted | Truth | Flagged? |
|---|---|---|---|---|
| inv03-us-pdf | vendor_name | GRANITE STATE LOGISTICS | Summit Peak Marketing Inc. | **NO** |
| inv03-us-pdf | customer_name | Summit Peak Marketing Inc. | Granite State Logistics | **NO** |
| inv04-us-pdf | line_items | 49 lines, sum 42,644.53 | 48 lines, sum 42,604.63 | yes: looks like a shipping/fee charge, not an item: Shipping |
| inv07-uk-pdf | vendor_name | HARROW & FINCH SOLICITORS | Kestrel Print Studio Ltd | **NO** |
| inv07-uk-pdf | customer_name | Kestrel Print Studio Ltd | Harrow & Finch Solicitors | **NO** |
| inv10-de-pdf | line_items | 49 lines, sum 35,903.36 | 48 lines, sum 35,888.36 | yes: looks like a shipping/fee charge, not an item: Versandkosten |
| inv11-de-pdf | vendor_name | KESSLER LOGISTIK AG | Lindqvist Software GmbH | **NO** |
| inv11-de-pdf | customer_name | Lindqvist Software GmbH | Kessler Logistik AG | **NO** |
| inv16-fr-pdf | vendor_name | BOULANGERIE PETIT | Dubois Informatique | **NO** |
| inv16-fr-pdf | customer_name | Dubois Informatique | Boulangerie Petit | **NO** |

## False alarms

- none
