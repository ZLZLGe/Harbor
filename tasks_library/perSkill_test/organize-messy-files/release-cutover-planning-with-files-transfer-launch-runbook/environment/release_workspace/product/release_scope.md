# Commerce Web Release 2026.04.08-rc2

- Release identifier: `2026.04.08-rc2`
- Maintenance window: `2026-04-08 21:00-22:15 UTC`
- Launch bridge: `#commerce-cutover`
- Scope:
  - `checkout-api`
  - `customer-portal`
  - `billing-worker`
- Feature flags to activate after deploy:
  - `ledger_dual_write`
  - `express_wallet`
- Customer-facing expectation: keep checkout in maintenance mode during schema work and reopen only after smoke tests and metric checks succeed.
- Change ticket: `CHG-902`
