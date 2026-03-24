Review these files:
- `/root/payment_requests.csv`: exported vendor payment requests.
- `/root/approved_vendor_ledger.json`: approved vendors with canonical `vendor_id`, `vendor_name`, and authorized bank account.
- `/root/purchase_orders.csv`: valid purchase orders with `po_number`, `vendor_id`, and approved amount.

Write `/root/payment_anomalies.json` containing only the flagged payment requests.

A payment request is flagged if it meets any of the following conditions:
1. `Unknown Vendor`: the submitted vendor name cannot be reliably matched to any vendor in the approved ledger. Request names may contain abbreviations, punctuation changes, spacing differences, or small misspellings.
2. `Bank Account Mismatch`: the vendor can be matched, but the submitted bank account does not equal the authorized bank account for that vendor.
3. `Invalid PO`: the PO number is missing or does not exist in `purchase_orders.csv`.
4. `Amount Mismatch`: the PO exists, but the requested amount differs from the approved PO amount by more than `0.01`.
5. `Vendor Mismatch`: the PO exists, but it belongs to a different `vendor_id` than the matched vendor.

If multiple conditions apply, use the first matching reason in the order above.

Output requirements:
- Keep only flagged requests in the JSON array.
- Preserve the original submitted vendor text in the output field `vendor_name`.
- Use `null` for `po_number` when the request has no PO number.
- Each object must have this structure:

```json
[
  {
    "request_id": "REQ-002",
    "vendor_name": "Blue Harbor Supply Co.",
    "requested_amount": 9430.5,
    "bank_account": "US00-BH-000000",
    "po_number": "PO-91002",
    "reason": "Bank Account Mismatch"
  }
]
```
