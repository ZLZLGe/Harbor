A recent regression in `/workspace/text-normalizer` changed how display text is normalized before it is stored.

Start in `/workspace/text-normalizer` and reproduce the failing test run. The intended behavior is documented in `CONTRACT.md`.

Update the project so that:
- the normalization logic matches the documented contract again,
- `tests/test_normalizer.py` is strengthened with focused case variations instead of relying on a single narrow regression check,
- the full test suite passes.

Write `artifacts/normalizer-regression-notes.md` with these sections:
- `## Broken cases`
- `## Test updates`
- `## Implementation fix`

Each section should briefly describe what was broken, which cases you added, and how you changed the code.
