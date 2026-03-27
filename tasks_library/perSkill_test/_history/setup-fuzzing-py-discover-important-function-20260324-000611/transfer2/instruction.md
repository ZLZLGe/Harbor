Inspect the Python monorepo at `/root/repos/opssuite` and create `/root/transfer2_boundary_map.tsv`.

Use this exact tab-separated header:
`rank	path	symbol	risk_kind	test_signal`

Requirements:
- list exactly six rows, ranked from `1` to `6`
- `path` must be repository-relative
- `symbol` must be a fully qualified function name
- `risk_kind` must be a short lowercase label such as `json`, `binary`, `template`, `yaml`, or `index`
- `test_signal` must be the most relevant existing test file
