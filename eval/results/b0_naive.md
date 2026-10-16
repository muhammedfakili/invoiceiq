# B0 — No-schema experiment (gemini / gemini-3.5-flash-lite, 2026-10-12 22:40)

## northwind.pdf

**True values:** vendor=Northwind Office Supply, customer=Cedar Ridge Accounting LLC, invoice_number=INV-1042, invoice_date=2026-03-04, currency=USD, subtotal=1250.0, tax=102.0, total=1377.0, amount_due=1377.0

<details><summary>Text sent to the LLM</summary>

```
NORTHWIND OFFICE SUPPLY INVOICE
2150 Market Street, Denver, CO 80205 | billing@northwind-supply.example
Invoice #: INV-1042
Date: 03/04/2026
Bill To:
Terms: Net 30
Cedar Ridge Accounting LLC
88 Pine Ave, Boulder, CO 80302
Description Qty Unit Price Amount
Ergonomic office chair 5 189.00 945.00
Standing desk mat 5 45.00 225.00
Printer paper, case of 10 reams 2 40.00 80.00
Subtotal 1,250.00
Shipping 25.00
Sales Tax (8%) 102.00
TOTAL (USD) $1,377.00
Thank you for your business! Please pay within 30 days.
```

</details>

### [plain]

Here is the extracted data from the invoice:

**Vendor Details:**
* **Name:** Northwind Office Supply
* **Address:** 2150 Market Street, Denver, CO 80205
* **Email:** billing@northwind-supply.example

**Invoice Details:**
* **Invoice Number:** INV-1042
* **Date:** 03/04/2026
* **Payment Terms:** Net 30

**Bill To:**
* **Customer Name:** Cedar Ridge Accounting LLC
* **Address:** 88 Pine Ave, Boulder, CO 80302

**Line Items:**
1. **Ergonomic office chair**
   * Quantity: 5
   * Unit Price: $189.00
   * Amount: $945.00
2. **Standing desk mat**
   * Quantity: 5
   * Unit Price: $45.00
   * Amount: $225.00
3. **Printer paper, case of 10 reams**
   * Quantity: 2
   * Unit Price: $40.00
   * Amount: $80.00

**Totals:**
* **Subtotal:** $1,250.00
* **Shipping:** $25.00
* **Sales Tax (8%):** $102.00
* **TOTAL (USD):** $1,377.00

### [json]

```json
{
  "invoice_number": "INV-1042",
  "invoice_date": "03/04/2026",
  "terms": "Net 30",
  "vendor": {
    "name": "Northwind Office Supply",
    "address": "2150 Market Street, Denver, CO 80205",
    "email": "billing@northwind-supply.example"
  },
  "bill_to": {
    "company": "Cedar Ridge Accounting LLC",
    "address": "88 Pine Ave, Boulder, CO 80302"
  },
  "line_items": [
    {
      "description": "Ergonomic office chair",
      "quantity": 5,
      "unit_price": 189.00,
      "amount": 945.00
    },
    {
      "description": "Standing desk mat",
      "quantity": 5,
      "unit_price": 45.00,
      "amount": 225.00
    },
    {
      "description": "Printer paper, case of 10 reams",
      "quantity": 2,
      "unit_price": 40.00,
      "amount": 80.00
    }
  ],
  "subtotal": 1250.00,
  "shipping": 25.00,
  "sales_tax": 102.00,
  "total": 1377.00,
  "currency": "USD"
}
```

### [json#2]

```json
{
  "invoice_number": "INV-1042",
  "invoice_date": "03/04/2026",
  "terms": "Net 30",
  "vendor": {
    "name": "Northwind Office Supply",
    "address": "2150 Market Street, Denver, CO 80205",
    "email": "billing@northwind-supply.example"
  },
  "bill_to": {
    "company_name": "Cedar Ridge Accounting LLC",
    "address": "88 Pine Ave, Boulder, CO 80302"
  },
  "line_items": [
    {
      "description": "Ergonomic office chair",
      "quantity": 5,
      "unit_price": 189.00,
      "amount": 945.00
    },
    {
      "description": "Standing desk mat",
      "quantity": 5,
      "unit_price": 45.00,
      "amount": 225.00
    },
    {
      "description": "Printer paper, case of 10 reams",
      "quantity": 2,
      "unit_price": 40.00,
      "amount": 80.00
    }
  ],
  "subtotal": 1250.00,
  "shipping": 25.00,
  "tax": 102.00,
  "total": 1377.00,
  "currency": "USD"
}
```

## brandt.pdf

**True values:** vendor=Brandt Elektrotechnik GmbH, customer=Kessler Logistik AG, invoice_number=RE-2026-0318, invoice_date=2026-03-12, currency=EUR, subtotal=1234.5, tax=234.56, total=1469.06, amount_due=1469.06

<details><summary>Text sent to the LLM</summary>

```
Brandt Elektrotechnik GmbH
Industriestraße 14 · 70565 Stuttgart · USt-IdNr. DE 287 445 190
Kessler Logistik AG Rechnungsnummer: RE-2026-0318
Hafenweg 3 Rechnungsdatum: 12.03.2026
20457 Hamburg Lieferdatum: 09.03.2026
Kundennummer: 40711
RECHNUNG
Bezeichnung Menge Einzelpreis Gesamt
LED-Hallenleuchte 150 W 6 142,50 € 855,00 €
Montage und Anschluss (Std.) 4 82,00 € 328,00 €
Anfahrtspauschale 1 51,50 € 51,50 €
Nettobetrag 1.234,50 €
zzgl. 19 % MwSt. 234,56 €
Rechnungsbetrag 1.469,06 €
Zahlbar innerhalb von 14 Tagen ohne Abzug.
IBAN: DE44 6005 0101 0004 2871 33 · BIC: SOLADEST600
```

</details>

### [plain]

```json
{
  "invoice_number": "RE-2026-0318",
  "invoice_date": "12.03.2026",
  "delivery_date": "09.03.2026",
  "customer_number": "40711",
  "vendor": {
    "name": "Brandt Elektrotechnik GmbH",
    "address": "Industriestraße 14 · 70565 Stuttgart",
    "vat_id": "DE 287 445 190"
  },
  "customer": {
    "name": "Kessler Logistik AG",
    "address": "Hafenweg 3\n20457 Hamburg"
  },
  "line_items": [
    {
      "description": "LED-Hallenleuchte 150 W",
      "quantity": 6,
      "unit_price": 142.50,
      "total_price": 855.00
    },
    {
      "description": "Montage und Anschluss (Std.)",
      "quantity": 4,
      "unit_price": 82.00,
      "total_price": 328.00
    },
    {
      "description": "Anfahrtspauschale",
      "quantity": 1,
      "unit_price": 51.50,
      "total_price": 51.50
    }
  ],
  "totals": {
    "net_amount": 1234.50,
    "tax_rate": 19,
    "tax_amount": 234.56,
    "gross_amount": 1469.06
  },
  "payment_terms": "Zahlbar innerhalb von 14 Tagen ohne Abzug.",
  "bank_details": {
    "iban": "DE44 6005 0101 0004 2871 33",
    "bic": "SOLADEST600"
  }
}
```

### [json]

```json
{
  "invoice_number": "RE-2026-0318",
  "invoice_date": "12.03.2026",
  "delivery_date": "09.03.2026",
  "customer_number": "40711",
  "supplier": {
    "name": "Brandt Elektrotechnik GmbH",
    "address": "Industriestraße 14 · 70565 Stuttgart",
    "vat_id": "DE 287 445 190"
  },
  "customer": {
    "name": "Kessler Logistik AG",
    "address": "Hafenweg 3\n20457 Hamburg"
  },
  "line_items": [
    {
      "description": "LED-Hallenleuchte 150 W",
      "quantity": 6,
      "unit_price": 142.50,
      "total_price": 855.00
    },
    {
      "description": "Montage und Anschluss (Std.)",
      "quantity": 4,
      "unit_price": 82.00,
      "total_price": 328.00
    },
    {
      "description": "Anfahrtspauschale",
      "quantity": 1,
      "unit_price": 51.50,
      "total_price": 51.50
    }
  ],
  "net_amount": 1234.50,
  "tax_amount": 234.56,
  "tax_rate": 19,
  "total_amount": 1469.06,
  "payment_terms": "Zahlbar innerhalb von 14 Tagen ohne Abzug.",
  "bank_details": {
    "iban": "DE44 6005 0101 0004 2871 33",
    "bic": "SOLADEST600"
  }
}
```

### [json#2]

```json
{
  "invoice_number": "RE-2026-0318",
  "invoice_date": "12.03.2026",
  "delivery_date": "09.03.2026",
  "customer_number": "40711",
  "supplier": {
    "company_name": "Brandt Elektrotechnik GmbH",
    "address": "Industriestraße 14 · 70565 Stuttgart",
    "vat_id": "DE 287 445 190",
    "bank_details": {
      "iban": "DE44 6005 0101 0004 2871 33",
      "bic": "SOLADEST600"
    }
  },
  "customer": {
    "company_name": "Kessler Logistik AG",
    "address": "Hafenweg 3\n20457 Hamburg"
  },
  "line_items": [
    {
      "description": "LED-Hallenleuchte 150 W",
      "quantity": 6,
      "unit_price": 142.50,
      "total_price": 855.00
    },
    {
      "description": "Montage und Anschluss (Std.)",
      "quantity": 4,
      "unit_price": 82.00,
      "total_price": 328.00
    },
    {
      "description": "Anfahrtspauschale",
      "quantity": 1,
      "unit_price": 51.50,
      "total_price": 51.50
    }
  ],
  "net_amount": 1234.50,
  "tax_amount": 234.56,
  "tax_rate_percent": 19,
  "gross_amount": 1469.06,
  "payment_terms": "Zahlbar innerhalb von 14 Tagen ohne Abzug."
}
```

## harbor.pdf

**True values:** vendor=Harbor Creative Studio, customer=Pinewood Dental Group, invoice_number=HCS-2026-019, invoice_date=2026-05-07, currency=USD, subtotal=2400.0, tax=0.0, total=2400.0, amount_due=1600.0

<details><summary>Text sent to the LLM</summary>

```
Prepared for Harbor Creative Studio
PINEWOOD DENTAL GROUP
12 Canal St, Duluth, MN 55802
hello@harborcreative.example
410 Lakeshore Blvd, Suite 200, Duluth, MN 55802
Invoice HCS-2026-019 · Issued May 7, 2026 · Due June 6, 2026
Service Hours Rate Amount
Brand refresh: logo and colour system 16 95.00 1,520.00
Website landing page design 8 95.00 760.00
Stock photography licence 1 120.00 120.00
Total $2,400.00
Deposit received (Apr 2) -$800.00
Balance due $1,600.00
Services are not subject to sales tax in this engagement.
```

</details>

### [plain]

```json
{
  "invoice_number": "HCS-2026-019",
  "issue_date": "2026-05-07",
  "due_date": "2026-06-06",
  "vendor": {
    "name": "Harbor Creative Studio",
    "address": "12 Canal St, Duluth, MN 55802",
    "email": "hello@harborcreative.example"
  },
  "client": {
    "name": "Pinewood Dental Group",
    "address": "410 Lakeshore Blvd, Suite 200, Duluth, MN 55802"
  },
  "line_items": [
    {
      "description": "Brand refresh: logo and colour system",
      "hours": 16.0,
      "rate": 95.00,
      "amount": 1520.00
    },
    {
      "description": "Website landing page design",
      "hours": 8.0,
      "rate": 95.00,
      "amount": 760.00
    },
    {
      "description": "Stock photography licence",
      "hours": 1.0,
      "rate": 120.00,
      "amount": 120.00
    }
  ],
  "subtotal": 2400.00,
  "deposits_received": [
    {
      "date": "2026-04-02",
      "amount": -800.00
    }
  ],
  "balance_due": 1600.00,
  "tax_note": "Services are not subject to sales tax in this engagement."
}
```

### [json]

```json
{
  "invoice_number": "HCS-2026-019",
  "issue_date": "2026-05-07",
  "due_date": "2026-06-06",
  "vendor": {
    "name": "Harbor Creative Studio",
    "address": "410 Lakeshore Blvd, Suite 200, Duluth, MN 55802"
  },
  "client": {
    "name": "Pinewood Dental Group",
    "address": "12 Canal St, Duluth, MN 55802",
    "email": "hello@harborcreative.example"
  },
  "line_items": [
    {
      "description": "Brand refresh: logo and colour system",
      "hours": 16,
      "rate": 95.00,
      "amount": 1520.00
    },
    {
      "description": "Website landing page design",
      "hours": 8,
      "rate": 95.00,
      "amount": 760.00
    },
    {
      "description": "Stock photography licence",
      "hours": 1,
      "rate": 120.00,
      "amount": 120.00
    }
  ],
  "subtotal": 2400.00,
  "deposit_received": {
    "date": "2026-04-02",
    "amount": -800.00
  },
  "balance_due": 1600.00,
  "tax": 0.00
}
```

### [json#2]

```json
{
  "invoice_number": "HCS-2026-019",
  "issue_date": "May 7, 2026",
  "due_date": "June 6, 2026",
  "vendor": {
    "name": "Harbor Creative Studio",
    "address": "410 Lakeshore Blvd, Suite 200, Duluth, MN 55802",
    "email": "hello@harborcreative.example"
  },
  "client": {
    "name": "Pinewood Dental Group",
    "address": "12 Canal St, Duluth, MN 55802"
  },
  "line_items": [
    {
      "description": "Brand refresh: logo and colour system",
      "hours": 16,
      "rate": 95.00,
      "amount": 1520.00
    },
    {
      "description": "Website landing page design",
      "hours": 8,
      "rate": 95.00,
      "amount": 760.00
    },
    {
      "description": "Stock photography licence",
      "hours": 1,
      "rate": 120.00,
      "amount": 120.00
    }
  ],
  "subtotal": 2400.00,
  "deposit_received": {
    "date": "Apr 2",
    "amount": -800.00
  },
  "balance_due": 1600.00,
  "tax_note": "Services are not subject to sales tax in this engagement."
}
```

## ashford.pdf

**True values:** vendor=Ashford & Lane Ltd, customer=Moorgate Cafés Ltd, invoice_number=AL-7781, invoice_date=2026-03-04, currency=GBP, subtotal=900.0, tax=180.0, total=1080.0, amount_due=1080.0

<details><summary>Text sent to the LLM</summary>

```
Ashford & Lane Ltd TAX INVOICE
Unit 7, Riverside Works, Leeds LS11 5QR · VAT Reg. GB 318 2204 57
Invoice to: Invoice No: AL-7781
Moorgate Cafés Ltd Your PO: PO-55120
3 Kirkgate, York YO1 8AA Order date: 28/02/2026
Invoice date: 04/03/2026
Payment due: 03/04/2026
Item Qty Unit £ Net £
Espresso machine descaling service 4 150.00 600.00
Grinder burr replacement 4 100.00 400.00
Loyalty discount 10% -100.00
Net total £900.00
VAT @ 20% £180.00
Amount payable £1,080.00
```

</details>

### [plain]

Here is the extracted data from the invoice, formatted for the accounting team:

**Supplier Information**
* **Company Name:** Ashford & Lane Ltd
* **Address:** Unit 7, Riverside Works, Leeds LS11 5QR
* **VAT Registration Number:** GB 318 2204 57

**Invoice Details**
* **Invoice Number:** AL-7781
* **Invoice Date:** 04/03/2026
* **Order Date:** 28/02/2026
* **Payment Due Date:** 03/04/2026
* **Purchase Order (PO) Number:** PO-55120

**Customer Information**
* **Invoice To:** Moorgate Cafés Ltd
* **Address:** 3 Kirkgate, York YO1 8AA

**Line Items**
1. **Espresso machine descaling service**
   * Quantity: 4
   * Unit Price: £150.00
   * Net Amount: £600.00
2. **Grinder burr replacement**
   * Quantity: 4
   * Unit Price: £100.00
   * Net Amount: £400.00
3. **Loyalty discount (10%)**
   * Net Amount: -£100.00

**Financial Summary**
* **Net Total:** £900.00
* **VAT (@ 20%):** £180.00
* **Amount Payable:** £1,080.00

### [json]

```json
{
  "supplier": {
    "name": "Ashford & Lane Ltd",
    "address": "Unit 7, Riverside Works, Leeds LS11 5QR",
    "vat_reg_no": "GB 318 2204 57"
  },
  "customer": {
    "name": "Moorgate Cafés Ltd",
    "address": "3 Kirkgate, York YO1 8AA"
  },
  "invoice_details": {
    "invoice_no": "AL-7781",
    "purchase_order": "PO-55120",
    "order_date": "28/02/2026",
    "invoice_date": "04/03/2026",
    "payment_due_date": "03/04/2026"
  },
  "line_items": [
    {
      "description": "Espresso machine descaling service",
      "quantity": 4,
      "unit_price_gbp": 150.00,
      "net_gbp": 600.00
    },
    {
      "description": "Grinder burr replacement",
      "quantity": 4,
      "unit_price_gbp": 100.00,
      "net_gbp": 400.00
    },
    {
      "description": "Loyalty discount 10%",
      "quantity": null,
      "unit_price_gbp": null,
      "net_gbp": -100.00
    }
  ],
  "totals": {
    "net_total_gbp": 900.00,
    "vat_amount_gbp": 180.00,
    "amount_payable_gbp": 1080.00
  }
}
```

### [json#2]

```json
{
  "supplier": {
    "name": "Ashford & Lane Ltd",
    "address": "Unit 7, Riverside Works, Leeds LS11 5QR",
    "vat_number": "GB 318 2204 57"
  },
  "invoice_to": {
    "company_name": "Moorgate Cafés Ltd",
    "address": "3 Kirkgate, York YO1 8AA"
  },
  "invoice_details": {
    "invoice_number": "AL-7781",
    "purchase_order": "PO-55120",
    "order_date": "28/02/2026",
    "invoice_date": "04/03/2026",
    "payment_due": "03/04/2026"
  },
  "line_items": [
    {
      "description": "Espresso machine descaling service",
      "quantity": 4,
      "unit_price_gbp": 150.00,
      "net_gbp": 600.00
    },
    {
      "description": "Grinder burr replacement",
      "quantity": 4,
      "unit_price_gbp": 100.00,
      "net_gbp": 400.00
    },
    {
      "description": "Loyalty discount 10%",
      "quantity": null,
      "unit_price_gbp": null,
      "net_gbp": -100.00
    }
  ],
  "totals": {
    "net_total_gbp": 900.00,
    "vat_gbp": 180.00,
    "amount_payable_gbp": 1080.00
  }
}
```

## Summary: keys in the JSON answers

| Invoice | Call | JSON parsed | Key count | Top-level keys |
|---|---|---|---|---|
| northwind | json | yes | 16 | `invoice_number, invoice_date, terms, vendor, bill_to, line_items, subtotal, shipping, sales_tax, total, currency` |
| northwind | json#2 | yes | 16 | `invoice_number, invoice_date, terms, vendor, bill_to, line_items, subtotal, shipping, tax, total, currency` |
| brandt | json | yes | 20 | `invoice_number, invoice_date, delivery_date, customer_number, supplier, customer, line_items, net_amount, tax_amount, tax_rate, total_amount, payment_terms, bank_details` |
| brandt | json#2 | yes | 20 | `invoice_number, invoice_date, delivery_date, customer_number, supplier, customer, line_items, net_amount, tax_amount, tax_rate_percent, gross_amount, payment_terms` |
| harbor | json | yes | 17 | `invoice_number, issue_date, due_date, vendor, client, line_items, subtotal, deposit_received, balance_due, tax` |
| harbor | json#2 | yes | 17 | `invoice_number, issue_date, due_date, vendor, client, line_items, subtotal, deposit_received, balance_due, tax_note` |
| ashford | json | yes | 18 | `supplier, customer, invoice_details, line_items, totals` |
| ashford | json#2 | yes | 18 | `supplier, invoice_to, invoice_details, line_items, totals` |

## Summary: could a program find the keys `vendor`, `invoice_date`, `total`, `amount_due`?

| Invoice | Call | vendor | invoice_date | total | amount_due |
|---|---|---|---|---|---|
| northwind | json | {'name': 'Northwind Office Supply', 'address': '2150 Market Street, Denver, CO 80205', 'email': 'billing@northwind-supply.example'} | 03/04/2026 | 1377.0 | — |
| northwind | json#2 | {'name': 'Northwind Office Supply', 'address': '2150 Market Street, Denver, CO 80205', 'email': 'billing@northwind-supply.example'} | 03/04/2026 | 1377.0 | — |
| brandt | json | — | 12.03.2026 | — | — |
| brandt | json#2 | — | 12.03.2026 | — | — |
| harbor | json | {'name': 'Harbor Creative Studio', 'address': '410 Lakeshore Blvd, Suite 200, Duluth, MN 55802'} | — | — | — |
| harbor | json#2 | {'name': 'Harbor Creative Studio', 'address': '410 Lakeshore Blvd, Suite 200, Duluth, MN 55802', 'email': 'hello@harborcreative.example'} | — | — | — |
| ashford | json | — | — | — | — |
| ashford | json#2 | — | — | — | — |