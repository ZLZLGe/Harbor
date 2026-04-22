# cdc-lakehouse-publish

Use this skill when a task asks you to recover or deliver a publishable data-engineering snapshot from raw operational feeds, especially when the environment contains CDC, schema evolution, batch warehouse outputs, data-quality checks, and a live publish or audit endpoint.

This skill is for:

- CDC finalization and replay-safe latest-version selection
- schema drift normalization across amount / timestamp fields
- timezone-aware SLA or freshness calculations
- warehouse publishing with manifest-driven bundle construction
- validating that final outputs and live receipts refer to the same canonical payload

Do not use this skill to hardcode outputs or bypass the live publish chain.

## Workflow

1. Read the visible source and metric contracts before changing code.
2. Fetch the live manifest first so you know the expected snapshot and publish contract.
3. Use the provided probe to query the audit service's diagnostic view of the raw feeds and current warehouse.
4. Repair the warehouse tables around the highest-signal issues first.
5. Prefer the provided helper scripts for probing and publish, because they bootstrap the local audit service if it is not already listening.
6. Construct the publish bundle from the final warehouse, not from guessed constants.
7. Submit the final bundle through the live publish endpoint and persist the live receipt.

## Helper Scripts

### Probe raw inputs

```bash
probe_marketplace_snapshot
```

This prints the live manifest plus the audit service's current diagnostics:

- replay-conflict rows where a replay-safe latest-version rule matters
- amount-drift examples that need field normalization
- timezone-sensitive shipment rows whose SLA classification can flip
- if a warehouse already exists, per-table mismatch summaries against the live audit reference

### Build canonical publish bundle and submit it

```bash
submit_marketplace_bundle
```

This expects `/app/output/warehouse.duckdb` to already exist. It fetches the live manifest, computes canonical table hashes and row counts from the final warehouse, writes `/app/output/publish_bundle.json`, submits it to the live publish endpoint, and writes `/app/output/publish_receipt.json`.

### End-to-end build and publish

```bash
build_and_publish_marketplace_snapshot
```

This runs the workspace build entrypoint and then uses the canonical publish workflow above.

### Fast validation against main data and synthetic edge cases

```bash
python3 /opt/task-skills/cdc-lakehouse-publish/validate_marketplace_snapshot.py
```

Use this after data-fix edits. It bootstraps the local audit service, validates the current workspace logic against the frozen main data plus a synthetic edge fixture that stresses replay-safe CDC selection, amount-field normalization, and UTC-based SLA logic, and prints a compact pass/fail summary with row counts and bundle metadata. When the verifier's alternate fixture is available, it will also include an `alt` section, but do not rely on that being present during agent execution.

## Things To Watch

- `snapshot_date` is a UTC date, not a source-local date.
- replay-safe latest-version semantics matter more than source file order.
- amount fields may drift during feed migrations; normalize before aggregating.
- same `event_seq` rows can still require an `ingested_at` tie-break.
- live receipt hashes must match the canonical final bundle, not an earlier draft.
