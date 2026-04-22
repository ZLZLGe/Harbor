# Release Diagnostics Reference

- A healthy run should call the broker for candidates, provenance, and promotion plan.
- `stable` and `deployable` are intentionally different concepts.
- If `promotion-plan.json` falls back to a historical snapshot, keep tracing upstream until the live broker plan and bundle agree on deployable artifact ids.
