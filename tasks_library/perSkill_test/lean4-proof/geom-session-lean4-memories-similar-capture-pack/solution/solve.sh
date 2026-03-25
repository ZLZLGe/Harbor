#!/bin/bash

set -euo pipefail

mkdir -p /app/artifacts

cat > /app/artifacts/geom-session-memory-pack.json <<'EOF'
{
  "session_id": "geom-bound-session",
  "source_files": [
    "/app/session_assets/geom_bound_session.lean",
    "/app/session_assets/failed_attempts.md",
    "/app/session_assets/project_conventions.md"
  ],
  "proof_patterns": [
    {
      "name": "closed-form-then-bound",
      "goal_shape": "Show an upper bound for a recursively defined rational sequence by converting the recurrence into a closed form.",
      "strategy": "First prove `G n = 2 - 2 / 3^(n + 1)` by induction, rewriting the recurrence with `rw [G]`, substituting the induction hypothesis, and normalizing with `ring_nf` and `ring`; then prove the tail term is positive and finish the strict inequality with `linarith`.",
      "supporting_details": {
        "tactics": ["induction", "rw", "ring_nf", "ring", "positivity", "linarith"],
        "helper_lemmas": ["h_closed", "h_tail_pos"]
      },
      "source_evidence": [
        {
          "file": "/app/session_assets/geom_bound_session.lean",
          "quote_or_line_hint": "theorem geom_bound: derive h_closed by induction, then use h_tail_pos and linarith"
        }
      ]
    }
  ],
  "failed_approaches": [
    {
      "name": "succ-case-linarith-before-rewrite",
      "attempted_step": "Trying `linarith [ih]` directly in the successor case of the closed-form proof.",
      "failure_signal": "`linarith failed to find a contradiction or derive the target`.",
      "why_it_failed": "The recurrence for `G` had not been unfolded, so the power term stayed nonlinear and opaque to `linarith`.",
      "better_direction": "Rewrite with `rw [G]`, plug in the induction hypothesis, and normalize algebraically with `ring_nf` and `ring` before using inequality automation.",
      "source_evidence": [
        {
          "file": "/app/session_assets/failed_attempts.md",
          "quote_or_line_hint": "Attempt A describes `linarith` too early in the induction step"
        }
      ]
    }
  ],
  "project_conventions": [
    {
      "name": "evidence-with-relative-paths",
      "rule": "Each reusable note should cite concrete evidence using repository-relative file paths.",
      "reason": "This keeps the captured memory traceable to the original session materials.",
      "source_evidence": [
        {
          "file": "/app/session_assets/project_conventions.md",
          "quote_or_line_hint": "Convention 1 requires concrete evidence with repository-relative file paths"
        }
      ]
    },
    {
      "name": "failed-note-must-include-alternative",
      "rule": "A failed-attempt note should record both the failure signal and the next better direction.",
      "reason": "The memory pack is meant to prevent repeated dead ends, not just archive errors.",
      "source_evidence": [
        {
          "file": "/app/session_assets/project_conventions.md",
          "quote_or_line_hint": "Convention 3 requires failure signal plus next better direction"
        }
      ]
    }
  ],
  "reuse_advice": [
    "For recurrence-based upper bounds, look for a closed form before pushing inequality tactics.",
    "If simplification only expands the recursion, stop and set up an induction lemma that exposes the tail term."
  ]
}
EOF
