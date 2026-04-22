# AGENTS

## Read Order

1. Read `specs/export_contract.md`, `specs/acceptance_criteria.md`, and `specs/quality_requirements.md`.
2. Read both incident notes under `incidents/` before editing exporter logic or quality assets.
3. Run the formal gate with `make quality-gate` to see current failures end to end.
4. Only then edit `settlement_quality/` and `quality/`.

## Working Rules

- Keep the formal stage order as `export -> validate -> summarize`.
- Keep both daily and monthly reports in scope.
- Do not bypass the local settlement gateway with static JSON or handwritten pass markers.
- Treat missing adjustments and blank batch ids as release-blocking regressions.
- Keep the formal `quality-gate` command as the canonical end-to-end check.

## Expected Close-Out

- `make quality-gate` exits successfully.
- `out/gate_result.json` shows both scenarios accepted.
- `out/export_summary.md` records the real gateway run and quality asset presence.
