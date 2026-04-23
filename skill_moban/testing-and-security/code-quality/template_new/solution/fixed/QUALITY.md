# Settlement Quality Standard

## Acceptance Bar

This repository is only release-ready when all of the following are true:

- `reference_batch` passes daily and monthly gateway acceptance.
- `dirty_incident_batch` passes daily and monthly gateway acceptance.
- `quality/test_functional.py` passes locally.
- `make quality-gate` exits non-zero on any validation failure and zero only when the full gate passes.

## Critical Risks

- Dirty adjustment events such as `refund`, `chargeback`, `manual_adjustment`, and `reserve_release` being silently dropped.
- Empty processor batch ids reaching the gateway instead of falling back to the batch id carried by the source record.
- Monthly summaries drifting away from daily semantics for gross, fee, adjustment, and net amounts.
- A patch that fixes current fixtures but breaks ordering stability or alternative merchant mixes.

## Required Scenarios

- `reference_batch`: healthy but mixed production-style traffic.
- `dirty_incident_batch`: reproduces the incident family where dirty data and batch-id gaps must still be accepted by the gateway.
- Alternate or shuffled fixtures: used to prove the exporter is behavior-driven rather than filename-driven or order-dependent.

## Evidence To Capture

- The exact gateway mismatch if a scenario fails.
- Which incident requirement or contract rule the failure violates.
- Whether the regression is in export logic, quality assets, or integration sequencing.
