A small importer in `/workspace/csv-metrics-lab` reads dashboard metrics from CSV, but a recent change started accepting malformed numeric fields and duplicate headers without reporting them correctly.

Start in `/workspace/csv-metrics-lab` and reproduce the failing test run. The intended import rules are documented in `METRICS_RULES.md`, and the sample feeds in `samples/` show the kinds of inputs this importer needs to handle.

Update the project so that:
- malformed numeric fields are rejected with row-level errors instead of being converted silently,
- duplicate headers stop the import with the documented file-level error,
- `tests/test_importer.py` is strengthened with compact case-driven coverage for accepted and rejected CSV inputs,
- the full test suite passes.

Write `artifacts/csv-validation-regression-log.md` with these sections:
- `## Accepted rows`
- `## Rejected rows`
- `## Importer changes`

Each section should briefly explain which CSV cases were covered and what changed in the importer.
