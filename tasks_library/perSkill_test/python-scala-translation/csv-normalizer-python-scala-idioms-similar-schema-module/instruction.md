# Similar - Schema-Driven CSV Normalizer Translation

`/root/CsvNormalizer.py` contains a Python module used to normalize partner CSV rows before they are loaded into an inventory pipeline. Translate it into idiomatic Scala 2.13 and save the result as `/root/CsvNormalizer.scala`.

Your Scala file must compile under Scala 2.13 and use package `csvnormalizer`.

Preserve the same domain behavior and expose the same translated public surface:

- `ColumnKind`
- `NormalizedValue`
- `ColumnSpec`
- `NormalizationIssue`
- `NormalizedRow`
- `class CsvNormalizer` with `headers`, `normalizeRow`, and `normalizeRows`
- `object CsvNormalizer` with `parseInteger`, `parseDecimal`, `parseFlag`, `parseTags`, and `catalogSchema`

Behavioral requirements:

- The schema must drive lookup by canonical source column plus aliases.
- Optional fields must stay optional in Scala instead of using sentinel strings or `null`.
- Missing required values and parse failures must be recorded as row issues without stopping later rows.
- `NormalizedRow.withMetadata` must append or overwrite row-level metadata entries.
- `CsvNormalizer.normalizeRows` must return an iterator-style result so rows are handled lazily over an input `Iterable`.

Data-modeling requirements:

- Model normalized cell values with a sealed hierarchy named `NormalizedValue`.
- Use `Option` for absent normalized values.
- Do not use `null` to represent missing data.

The bundled tests will compile your Scala file, run Scala unit tests against its behavior, and check the public API and the absence of `null`-based optional handling. `/root/sample_rows.json` is included only as a quick sanity-check asset.
