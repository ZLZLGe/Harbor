# Go / No-Go Notes

Date: 2026-04-08

Attendees and named release roles:

- Mara Singh: release manager and bridge lead
- Devon Hale: traffic controls and maintenance banner
- Priya Natarajan: database migration owner
- Linh Tran: application deploy owner
- Omar Ruiz: QA lead for launch-day validation

Decisions:

- `CHG-902` is approved for the maintenance window.
- No open P0 defects remain.
- No open P1 defect may block launch; `RL-219` and `RL-244` require targeted smoke validation after deployment.
- Sequence approved by the bridge:
  1. Confirm go / no-go and freeze deploys.
  2. Enable maintenance banner and drain checkout traffic.
  3. Pause `billing-worker` and take the pre-cutover snapshot.
  4. Run the ledger migration.
  5. Deploy `checkout-api` and `customer-portal`.
  6. Turn on `ledger_dual_write` and `express_wallet`.
  7. Execute launch smoke tests.
  8. Reopen traffic and monitor the bridge for 15 minutes before closing it.
