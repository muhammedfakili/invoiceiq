# Baseline: no schema (B0 approach) on 30 invoices

Model `gemini-3.5-flash-lite`. A program looks for each field name in the returned JSON.

| Field | Key present | Usable & correct |
|---|---|---|
| vendor_name | 1/30 | 1/30 |
| customer_name | 2/30 | 2/30 |
| invoice_number | 23/30 | 23/30 |
| invoice_date | 23/30 | 2/30 |
| due_date | 12/30 | 0/30 |
| currency | 13/30 | 12/30 |
| subtotal | 13/30 | 10/30 |
| tax | 4/30 | 4/30 |
| total | 11/30 | 11/30 |
| amount_due | 0/30 | 0/30 |
| line_items | 29/30 | 15/30 |

**Header field accuracy: 21.7%** (schema version: 100%)
