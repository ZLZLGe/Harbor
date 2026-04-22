---
name: exoplanet-workflows
description: Use when a task asks for multi-target exoplanet vetting from light-curve bundles and you need a concrete workflow for catalog fetch, manifest-aware cleaning, transit search, odd/even checks, secondary-eclipse checks, and final audit submission.
---

# Exoplanet Workflows

Use this skill when a task asks for exoplanet vetting or period finding from TESS-like light-curve data.

## Recommended workflow

For this task, prefer the task-specific one-command workflow first:

```bash
build_and_submit_catalog_vetting
```

That helper:
- fetches the live catalog
- fetches every live manifest
- performs the same cleaning and vetting workflow described below
- writes `/app/output/catalog_vetting.json`
- submits that exact bundle to the live `/audit` endpoint
- writes `/app/output/catalog_audit_receipt.json` with the exact verifier-facing schema

Important:
- Do not hand-write `catalog_audit_receipt.json`.
- Do not compute `request_sha256` in a custom script unless you are explicitly debugging the helper.
- The verifier checks that the receipt hash matches the canonical final bundle bytes. A common failure mode is: submit one payload, then mutate `catalog_vetting.json`, which leaves a stale `request_sha256`.
- If you build the bundle yourself, the final step must still be `build_and_submit_catalog_vetting` or `python /app/.codex/skills/exoplanet-workflows/submit_catalog_vetting.py`.

Use the manual steps below only if you want to inspect intermediate diagnostics or customize the final bundle.

1. Fetch the catalog first.
   - Start with `GET /catalog`.
   - Keep the returned `snapshot_id`.
   - Enumerate every required `target_id` before touching the final output.

2. Fetch a manifest for each target.
   - Use `GET /manifest/<target_id>`.
   - Respect `quarantine_windows_mjd`.
   - Keep `quality_points_removed` and `quarantine_points_removed` separate.

3. Clean and normalize per target.
   - Remove non-zero quality flags.
   - Remove manifest-quarantined cadences.
   - Normalize and detrend per sector.

4. Separate stellar variability from eclipse-like structure.
   - Use Lomb-Scargle on the cleaned but not transit-folded light curve for `rotation_alias_days`.
   - Use Box Least Squares on the flattened light curve for the strongest periodic dip.

5. Run eclipsing-binary diagnostics before finalizing the verdict.
   - Inspect `depth_odd` and `depth_even` from `BoxLeastSquares.compute_stats(...)`.
   - If odd/even mismatch is large, test the doubled-period interpretation.
   - Measure a secondary eclipse near phase 0.5 of the doubled-period solution when relevant.

6. Build the final bundle.
   - Write `/app/output/catalog_vetting.json` with top-level `snapshot_id` and `entries`.
   - Submit that exact bundle to `/audit`.
   - Save `/app/output/catalog_audit_receipt.json` as a compact receipt with exactly the workflow fields the task expects:
     - `request_sha256`
     - `accepted`
     - `snapshot_id`
     - `status`
     - `accepted_targets`
   - Do not dump the raw audit response directly into the receipt file.
   - Do not manually edit the receipt after submission; regenerate it from the helper instead.

## Fast diagnostic path for this task

Use the task-specific probe when you want diagnostics before finalizing:

```bash
python /app/.codex/skills/exoplanet-workflows/probe_catalog_vetting.py
```

The probe:
- fetches the live catalog and every live manifest
- computes cleaned counts, best BLS candidate, doubled-period checks, odd/even ratio, and secondary-eclipse SNR
- writes `/tmp/catalog_vetting_probe.json`
- includes `recommended_entries` derived from those diagnostics

For a report that already exists on disk, use the task-specific submit helper:

```bash
python /app/.codex/skills/exoplanet-workflows/submit_catalog_vetting.py
```

The submit helper:
- reads `/app/output/catalog_vetting.json`
- submits that exact payload to the live `/audit` endpoint
- computes the canonical `request_sha256`
- writes `/app/output/catalog_audit_receipt.json` in the exact schema the verifier expects

Suggested use:

1. Preferred path: run `build_and_submit_catalog_vetting` and then inspect the two final output files.
2. Diagnostic path: run the probe.
3. Open `/tmp/catalog_vetting_probe.json`.
4. Inspect `recommended_entries` and verify the bundle looks sane.
5. Write the final bundle to `/app/output/catalog_vetting.json`.
6. Run the submit helper to write the compact receipt. This step is required if you did not use `build_and_submit_catalog_vetting`.
7. Re-open both output files and sanity-check the final shape.

The probe is intentionally strong on workflow standardization, but it does not bypass the live catalog, manifest, or audit chain.
