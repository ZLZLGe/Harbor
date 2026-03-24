# CSV Metrics Import Rules

The importer reads small CSV feeds used by a dashboard pipeline.

Expected behavior:

1. The header row must contain the columns `metric`, `value`, and `unit`.
2. Header names must be unique. If the same header appears more than once, stop the import and record a single error with:
   - `line = 1`
   - `code = "duplicate-header"`
   - `message = "duplicate header: <name>"`
3. Whitespace around field values should be ignored.
4. The `value` field must parse as a floating-point number.
   - If parsing fails, skip that row and record an error with:
     - `code = "invalid-number"`
     - `message = "invalid numeric value '<raw>' for metric '<metric>'"`
5. Valid rows should still be imported even when other rows in the same file are rejected.
6. Imported records keep the original row order.
