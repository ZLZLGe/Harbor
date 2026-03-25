#!/bin/bash

set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"

mkdir -p "$APP_ROOT/artifacts"

APP_ROOT="$APP_ROOT" python3 - <<'PY'
import json
import os
from pathlib import Path


app = Path(os.environ["APP_ROOT"])
inputs = app / "handoff_inputs"
artifacts = app / "artifacts"

with (inputs / "collaborator_mira_export.json").open(encoding="utf-8") as f:
    mira = json.load(f)
with (inputs / "collaborator_noah_export.json").open(encoding="utf-8") as f:
    noah = json.load(f)
with (inputs / "project_file_inventory.json").open(encoding="utf-8") as f:
    inventory = json.load(f)

tracked_files = set(inventory["tracked_files"])

mira_records = {item["record_id"]: item for item in mira["records"]}
noah_records = {item["record_id"]: item for item in noah["records"]}

proof_pattern = {
    "record_id": "handoff-pp-recursive-bound-canonical",
    "record_type": "ProofPattern",
    "canonical_title": "Canonical recursive bound pattern: closed form first, then discharge the positive tail",
    "merged_from": [
        "mira-pp-recursive-bound-closed-form",
        "noah-pp-closed-form-tail-control",
    ],
    "decision_reason": (
        "Merged the two near-duplicate success records into one canonical pattern. "
        "Noah's export supplied broader evidence across multiple sessions, so it anchors the wording, "
        "while Mira's constant-minus-nonnegative-tail phrasing and minimal `ring` fallback were preserved."
    ),
    "source_evidence": [
        {"file": "Proofs/Sequences/GeomBound.lean", "line_hint": "theorem geom_bound"},
        {"file": "Proofs/Sequences/ThirdBound.lean", "line_hint": "theorem third_bound"},
        {"file": "Notes/session-geom-bound.md", "line_hint": "successful two-phase outline"},
        {"file": "Proofs/Sequences/HalfBound.lean", "line_hint": "theorem half_bound"},
    ],
    "goal_signals": sorted(
        set(mira_records["mira-pp-recursive-bound-closed-form"]["goal_signals"])
        | set(noah_records["noah-pp-closed-form-tail-control"]["goal_signals"])
    ),
    "recommended_steps": [
        "Use induction to derive an exact closed form before touching the top-level inequality.",
        "Rewrite the target as a constant minus a tail term, then prove the tail is nonnegative or positive.",
        "Normalize the algebraic shape with `ring_nf`, keeping plain `ring` available as a lighter fallback.",
        "Only after the recurrence is exposed should linear arithmetic or automation close the final bound.",
    ],
    "helper_lemmas": ["pow_pos", "ring", "ring_nf", "linarith"],
}

failed_records = [
    {
        "record_id": "handoff-fa-simp-recursion-too-early",
        "record_type": "FailedApproach",
        "canonical_title": mira_records["mira-fa-simp-recursion-too-early"]["title"],
        "merged_from": ["mira-fa-simp-recursion-too-early"],
        "decision_reason": "Kept as a distinct dead end because it warns against premature unfolding rather than premature linear arithmetic.",
        "source_evidence": mira_records["mira-fa-simp-recursion-too-early"]["evidence"],
        "attempted_step": mira_records["mira-fa-simp-recursion-too-early"]["attempted_step"],
        "failure_signal": mira_records["mira-fa-simp-recursion-too-early"]["failure_signal"],
        "better_direction": mira_records["mira-fa-simp-recursion-too-early"]["better_direction"],
    },
    {
        "record_id": "handoff-fa-linarith-before-unfolding",
        "record_type": "FailedApproach",
        "canonical_title": noah_records["noah-fa-linarith-before-unfolding"]["title"],
        "merged_from": ["noah-fa-linarith-before-unfolding"],
        "decision_reason": "Kept as a separate failure mode because it captures a different mistake than early simplification.",
        "source_evidence": noah_records["noah-fa-linarith-before-unfolding"]["evidence"],
        "attempted_step": noah_records["noah-fa-linarith-before-unfolding"]["attempted_step"],
        "failure_signal": noah_records["noah-fa-linarith-before-unfolding"]["failure_signal"],
        "better_direction": noah_records["noah-fa-linarith-before-unfolding"]["better_direction"],
    },
]

project_conventions = [
    {
        "record_id": "handoff-pc-evidence-citation",
        "record_type": "ProjectConvention",
        "canonical_title": "Canonical evidence citation rule for shared handoff packs",
        "merged_from": [
            "mira-pc-relative-evidence",
            "noah-pc-evidence-path-and-line",
        ],
        "decision_reason": (
            "Collapsed the overlapping citation rules into one stricter convention. "
            "The merged rule keeps Noah's stronger reviewability requirement and absorbs Mira's relative-path constraint."
        ),
        "source_evidence": [
            {"file": "Docs/memory-style.md", "line_hint": "section Evidence"},
            {"file": "Docs/memory-style.md", "line_hint": "section Reviewability"},
        ],
        "rule": "Every handoff memory must cite a repository-relative path plus a local line hint or theorem name.",
        "reason": "This is the narrowest rule that stays reviewable across collaborators and survives branch changes.",
    }
]

theorem_dependencies = [
    {
        "record_id": "handoff-td-pow-pos",
        "record_type": "TheoremDependency",
        "canonical_title": "Canonical positive-tail dependency uses an explicit positivity theorem",
        "merged_from": [
            "mira-td-positivity",
            "noah-td-pow-pos",
        ],
        "decision_reason": (
            "Preferred the explicit theorem dependency because it is easier to reuse and audit than an automation-only note. "
            "The tactic-level idea still survives inside the merged proof pattern instead of remaining a separate dependency record."
        ),
        "source_evidence": [
            {"file": "Proofs/Sequences/GeomBound.lean", "line_hint": "have h_pow_pos"},
            {"file": "Proofs/Sequences/ThirdBound.lean", "line_hint": "have h_den_pos"},
        ],
        "theorem": "pow_pos",
        "why_it_matters": "It gives an explicit positive-denominator bridge before the final inequality-closing step.",
        "preferred_source": "Proofs/Sequences/GeomBound.lean",
    }
]

merged = {
    "proof_patterns": [proof_pattern],
    "failed_approaches": failed_records,
    "project_conventions": project_conventions,
    "theorem_dependencies": theorem_dependencies,
}

for items in merged.values():
    for item in items:
        for evidence in item["source_evidence"]:
            if evidence["file"] not in tracked_files:
                raise ValueError(f"Missing tracked file for evidence: {evidence['file']}")
        if item["record_type"] == "TheoremDependency" and item["preferred_source"] not in tracked_files:
            raise ValueError(f"Missing tracked file for preferred_source: {item['preferred_source']}")

output = {
    "handoff_id": "collab-handoff-2026-03-memory-merge",
    "source_exports": [
        "/app/handoff_inputs/collaborator_mira_export.json",
        "/app/handoff_inputs/collaborator_noah_export.json",
        "/app/handoff_inputs/project_file_inventory.json",
        "/app/handoff_inputs/conflict_notes.md",
    ],
    "merge_summary": {
        "input_record_counts": {
            "collaborator_mira_export.json": len(mira["records"]),
            "collaborator_noah_export.json": len(noah["records"]),
        },
        "output_record_counts": {
            "proof_patterns": len(merged["proof_patterns"]),
            "failed_approaches": len(merged["failed_approaches"]),
            "project_conventions": len(merged["project_conventions"]),
            "theorem_dependencies": len(merged["theorem_dependencies"]),
        },
        "deduplicated_groups": [
            {
                "topic": "recursive upper-bound proof pattern",
                "merged_record_ids": [
                    "mira-pp-recursive-bound-closed-form",
                    "noah-pp-closed-form-tail-control",
                ],
                "kept_record_id": "handoff-pp-recursive-bound-canonical",
                "reason": "Both exports describe the same two-phase success pattern, so they were merged into a single canonical handoff record.",
            },
            {
                "topic": "evidence citation convention",
                "merged_record_ids": [
                    "mira-pc-relative-evidence",
                    "noah-pc-evidence-path-and-line",
                ],
                "kept_record_id": "handoff-pc-evidence-citation",
                "reason": "The handoff should expose only one reviewable citation rule, so the stricter version won and absorbed the simpler one.",
            },
            {
                "topic": "positive-tail dependency",
                "merged_record_ids": [
                    "mira-td-positivity",
                    "noah-td-pow-pos",
                ],
                "kept_record_id": "handoff-td-pow-pos",
                "reason": "The explicit theorem dependency was preferred over the tactic-only note for long-term reuse.",
            },
        ],
    },
    "merged_records": merged,
    "conflict_resolutions": [
        {
            "topic": "recursive upper-bound proof pattern",
            "winner_record_id": "handoff-pp-recursive-bound-canonical",
            "loser_record_ids": [
                "mira-pp-recursive-bound-closed-form",
                "noah-pp-closed-form-tail-control",
            ],
            "resolution_reason": "The final pattern uses Noah's stronger multi-session evidence as the canonical spine while preserving Mira's simpler tail-language and `ring` fallback.",
        },
        {
            "topic": "evidence citation convention",
            "winner_record_id": "handoff-pc-evidence-citation",
            "loser_record_ids": [
                "mira-pc-relative-evidence",
                "noah-pc-evidence-path-and-line",
            ],
            "resolution_reason": "A single stricter rule is easier to audit than two overlapping ones, so the canonical convention now requires both a repository-relative path and a local line hint or theorem name.",
        },
        {
            "topic": "positive-tail dependency",
            "winner_record_id": "handoff-td-pow-pos",
            "loser_record_ids": [
                "mira-td-positivity"
            ],
            "resolution_reason": "The explicit theorem-level dependency is more reusable and easier to verify, so the automation-only note was downgraded into supporting tactic detail inside the merged proof pattern.",
        },
    ],
    "dropped_records": [
        {
            "record_id": "mira-pc-relative-evidence",
            "drop_reason": "Absorbed into a stricter canonical citation convention.",
            "replaced_by": "handoff-pc-evidence-citation",
        },
        {
            "record_id": "noah-pc-evidence-path-and-line",
            "drop_reason": "Absorbed into the same canonical citation convention instead of surviving as a duplicate.",
            "replaced_by": "handoff-pc-evidence-citation",
        },
        {
            "record_id": "mira-td-positivity",
            "drop_reason": "Replaced by an explicit theorem dependency for positive-tail proofs.",
            "replaced_by": "handoff-td-pow-pos",
        },
    ],
    "handoff_guidance": [
        "Start future bound proofs by loading the canonical recursive-bound pattern and both failed approaches together; they describe the intended route and the two main dead ends.",
        "When adding new records, follow the single evidence convention in this handoff pack so later merges do not recreate citation conflicts.",
        "Treat `pow_pos` as the default reusable dependency for positive-tail arguments and record automation tactics only as supporting details inside a broader pattern.",
    ],
}

with (artifacts / "collab-handoff-memory-pack.json").open("w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
