Three Python repositories are available under `/root/repos`.

Inspect them and create `/root/transfer3_handoff_notes.json` as a JSON object keyed by repository name.

For each repository object, include:
- `selected_function`
- `important_test`
- `inferred_oracle`
- `review_note`

Requirements:
- include exactly these repositories: `packetlabels`, `schemabook`, `windowcalc`
- `selected_function` must be a fully qualified function name
- `important_test` must be the most relevant existing test file
- `inferred_oracle` must be a short sentence describing what the tests already prove
- `review_note` must be a short sentence describing the next boundary variation worth trying
