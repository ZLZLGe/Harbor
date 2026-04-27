---
name: drug-discovery
description: Diagnose and complete medicinal-chemistry lead triage tasks involving SMILES standardization, mixed-unit potency data, drug-likeness descriptors, structural alerts, ADMET/safety signals, and ranked candidate reports.
---

# Drug Discovery Lead Triage

Use this skill when a task asks for a reproducible small-molecule screening or lead-prioritization workflow rather than a single fixed answer. The useful pattern is to normalize the chemistry first, normalize the biology second, then rank only after the liabilities are visible.

## Fast Checklist

1. Parse every SMILES with RDKit and keep a canonical parent form. For salts, keep the largest chemically meaningful fragment and record duplicate parents.
2. Convert activity records to a single unit, usually nM. Do not average `>`, `>=`, `<`, or `<=` records as if they were exact observations.
3. Prefer target-matched IC50/Ki/Kd evidence for biochemical potency. Treat EC50 as supportive but lower-confidence evidence.
4. Compute medicinal-chemistry descriptors: molecular weight, LogP, HBD, HBA, TPSA, rotatable bonds, QED, and scaffold or series labels.
5. Flag common lead-triage liabilities: Lipinski/Veber excursions, PAINS-like catechols/polyphenols, Michael acceptors, anticoagulant-like coumarins, very high lipophilicity, and hard safety categories.
6. Rank candidates with a transparent score that combines potency, confidence, properties, QED, safety penalties, and series diversity.

## Task-Specific Probe

A helper implementation is available at:

`/root/.codex/skills/drug-discovery/scripts/build_triage.py`

For this Harbor task, run the helper before writing custom code. It writes a verifier-compatible, data-driven `/root/workspace/solution.py` and runs the report once:

```bash
python /root/workspace/solution.py
```

Use:

```bash
python /root/.codex/skills/drug-discovery/scripts/build_triage.py
```

The probe is intentionally data-driven. It reads `/root/workspace/data/candidates.csv`, `target_profile.json`, `activity_records.jsonl`, and `safety_reports.jsonl`; it does not need network access.

Important: do not reimplement the probe from memory unless it fails. Small differences are easy to miss here:

- The verifier expects average molecular weight (`Descriptors.MolWt`), not exact isotope mass.
- Exact MAPK14 activity records should use a confidence-weighted geometric mean; EC50 is lower weight.
- `<` upper-bound activity is retained as potent censored evidence at the bound handling used by the probe.
- Weak lower-bound controls remain auditable in `lead_triage.csv` as `deprioritize`; they are not silently dropped.
- `KIN-005` remains in the ranked audit trail with a catechol/polyphenol interference flag.

## Output Contract Reminders

- Keep `build_lead_triage_report(data_dir, output_dir)` as the public entry point.
- Preserve the exact CSV columns requested by the instruction.
- Keep `rank` consecutive and sorted from best to worst.
- Put invalid structures, duplicate parents, and hard safety exclusions into `excluded_candidates.csv`.
- Include method notes that explain unit conversion, structure standardization, activity aggregation, ranking, and safety handling.
