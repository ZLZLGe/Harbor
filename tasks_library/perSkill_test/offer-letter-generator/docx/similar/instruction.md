Write a completed offer letter document from the provided Word template.

Input files:
- `/root/offer_letter_template.docx`
- `/root/employee_data.json`

Output file:
- `/root/similar_offer_letter_filled.docx`

Requirements:
- replace all placeholders like `{{CANDIDATE_FULL_NAME}}`, `{{POSITION}}`, and similar fields with values from the JSON file
- process placeholders in body paragraphs, tables (including nested tables), headers, and footers
- handle the conditional relocation block marked by `{{IF_RELOCATION}}...{{END_IF_RELOCATION}}`
- if `RELOCATION_PACKAGE` is `Yes`, keep the inner relocation content but remove conditional markers
- if `RELOCATION_PACKAGE` is not `Yes`, remove the full conditional section content
- the final document must not contain any `{{...}}` placeholders or conditional markers
