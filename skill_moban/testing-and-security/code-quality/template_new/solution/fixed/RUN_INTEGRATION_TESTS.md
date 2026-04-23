# Run Integration Tests

## Command

```bash
make clean
make quality-gate
```

## Expected Behavior

- The gate exports both `reference_batch` and `dirty_incident_batch`.
- The local settlement gateway accepts both daily and monthly outputs for each scenario.
- `out/gate_result.json` and `out/export_summary.md` are regenerated on every run.

## What To Check If It Fails

- Read the mismatch details in `out/gate_result.json`.
- Confirm the gateway was actually called instead of a static fallback.
- Confirm batch ids are present in both reference and dirty outputs.
- Confirm the dirty incident batch still preserves negative adjustments and reserve releases.
