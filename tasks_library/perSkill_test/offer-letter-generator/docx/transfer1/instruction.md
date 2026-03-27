Generate a final offer letter document for one selected candidate.

Input files:
- `/root/offer_letter_template.docx`
- `/root/candidate_pool.json`

Output file:
- `/root/transfer1_selected_offer_letter.docx`

Requirements:
- read `selected_candidate_id` from the pool file and locate the matching candidate object
- use that selected candidate's fields to replace template placeholders
- process placeholders in body paragraphs, tables (including nested tables), headers, and footers
- process conditional block `{{IF_RELOCATION}}...{{END_IF_RELOCATION}}`
- if selected candidate has `RELOCATION_PACKAGE=Yes`, keep inner relocation content but remove markers
- otherwise remove the full relocation section content
- do not leave unresolved `{{...}}` tokens in the output document
