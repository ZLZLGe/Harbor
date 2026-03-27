Generate an offer letter by combining profile and terms data.

Input files:
- `/root/offer_letter_template.docx`
- `/root/profile_core.json`
- `/root/offer_terms.json`

Output file:
- `/root/transfer2_merged_offer_letter.docx`

Requirements:
- merge the two JSON files into one data record (terms should augment core profile fields)
- replace all placeholders in the template using merged data
- process placeholders in body paragraphs, nested tables, headers, and footers
- process conditional block `{{IF_RELOCATION}}...{{END_IF_RELOCATION}}`
- keep inner relocation content only when merged `RELOCATION_PACKAGE` is `Yes`
- otherwise remove the full relocation section content
- output must not contain unresolved template tokens
