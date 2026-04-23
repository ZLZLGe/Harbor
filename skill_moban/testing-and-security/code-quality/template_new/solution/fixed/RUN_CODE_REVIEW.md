# Run Code Review

## Review Goal

Reviewers are checking release readiness, not style alone. Every finding should connect to a user-visible or gateway-visible risk.

## Review Checklist

- Confirm `refund`, `chargeback`, `manual_adjustment`, and `reserve_release` all remain part of the export path.
- Confirm batch id fallback is taken from the source record when `processor_batch_id` is blank.
- Confirm monthly aggregation still matches daily semantics for gross, fee, adjustment, and net fields.
- Confirm the formal gate still goes through export, gateway validation, and summary generation.
- Confirm the patch does not replace real gateway calls with static evidence.

## Evidence Capture

- Quote the spec or incident file that justifies the finding.
- Point to a failing or newly added test when possible.
- Escalate any change that weakens failure semantics or shrinks scenario coverage.
