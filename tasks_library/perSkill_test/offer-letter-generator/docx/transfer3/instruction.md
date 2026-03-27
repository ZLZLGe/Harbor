Generate an offer letter by applying override fields on top of base data.

Input files:
- `/root/offer_letter_template.docx`
- `/root/base_data.json`
- `/root/overrides.json`

Output file:
- `/root/transfer3_overridden_offer_letter.docx`

Requirements:
- start from `base_data.json`, then override any matching keys using `overrides.json`
- use the resulting final data record to replace all placeholders in the template
- process placeholders in paragraphs, nested tables, headers, and footers
- process conditional block `{{IF_RELOCATION}}...{{END_IF_RELOCATION}}`
- keep the relocation content only when final `RELOCATION_PACKAGE` is `Yes`
- otherwise remove the full relocation conditional section
- final output must not contain unresolved `{{...}}` tokens
