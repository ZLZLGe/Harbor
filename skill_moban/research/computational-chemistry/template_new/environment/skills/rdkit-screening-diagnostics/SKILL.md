---
name: rdkit-screening-diagnostics
description: Diagnose and implement RDKit-based Python screening functions for Harbor computational-chemistry tasks. Use when solution.py must parse molecules, normalize structures, inspect sanitization behavior, compute descriptors, deduplicate deterministically, and apply task-provided rules without hardcoding answers.
---

# RDKit Screening Diagnostics

Use this skill when a task requires a Python screening function over local molecular files and the failure mode is likely to come from parse, normalization, descriptor, or deterministic ranking details rather than from one missing line of code.

## Workflow

1. Read the task contract and tests first. Do not infer thresholds, field names, ranking rules, or return schema from this skill.

2. Probe real parsing behavior before writing the final function:

```bash
python /root/.codex/skills/rdkit-screening-diagnostics/scripts/probe_parse.py /root/data/library
```

3. If the task involves deduplication or salts, compare normalization views and keep stereochemistry visible:

```bash
python /root/.codex/skills/rdkit-screening-diagnostics/scripts/probe_normalize.py /root/data/library
```

4. Confirm the descriptor API and rounding behavior on real task inputs:

```bash
python /root/.codex/skills/rdkit-screening-diagnostics/scripts/probe_descriptors.py /root/data/library
```

5. If the task asks for `inchikey` or another structure identifier, probe whether the runtime actually has InChI support before inventing a fallback:

```bash
python /root/.codex/skills/rdkit-screening-diagnostics/scripts/probe_inchi.py /root/data/library
```

6. After reading the task rules, project them onto the real compounds before finalizing `solution.py`:

```bash
python /root/.codex/skills/rdkit-screening-diagnostics/scripts/probe_rule_matrix.py \
  /root/data/library \
  /root/data/reference/rules.json
```

## Invariants

- Do not hardcode shortlist members, descriptor values, or alert results.
- Do not collapse stereoisomers just because their non-isomeric canonical SMILES match.
- Do not ignore salts or multi-fragment records when building the dedupe key.
- Do not guess descriptor variants: confirm whether the task expects `MolWt`, `TPSA`, `QED`, or another specific RDKit field.
- If the runtime lacks InChI support, do not fabricate pseudo-InChIKeys or hash-like stand-ins unless the task contract explicitly allows that format.
- When `inchikey` is required but unavailable from the runtime, prefer the task-prescribed fallback; if none is specified, use a deterministic chemistry-derived fallback such as canonical isomeric SMILES rather than an invented opaque identifier.
- Probe scripts are for diagnosis only. The final `solution.py` must stand on its own.
