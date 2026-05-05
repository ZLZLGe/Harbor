You are reviewing the live OrderHub API before partner handoff. The workspace already contains a runnable Node.js service and local data snapshots that define the allowed tenant scope.

Input data is in `/root/data`:
- `contracts/orderhub-public-openapi.yaml`: public API contract for the exposed endpoints.
- `engagement/target_profile.json`: target URL, allowed identities, and request budget.
- `engagement/rules_of_engagement.md`: local operating constraints for the review.
- `tenancy/account_map.json`: tenant-to-account mapping used by the service.
- `seed/`: order, customer, product, employee, shipper, and order-detail snapshots used by the API.

Your task:
1. Review the live API at `http://127.0.0.1:8142` and confirm the required security findings.
2. Produce a concise report with evidence files that show the observed behavior.
3. Stay within the provided request budget and use only the local target.

Output:
- Write `/root/output/security_findings.json`
- Write `/root/output/reproduction.md`
- Write `/root/output/evidence/`

Notes:
- Use the provided files under `/root/data` as the source of record for contract, tenancy, and seed data.
- Do not modify the service, the input data, or any skill files.
- Do not hardcode a fixed set of responses for the expected checks.
- Do not special-case individual order IDs, tenants, or query strings.
- Do not fetch external data at request time.
- Keep authentication, authorization, tenant scoping, rate limiting, and error handling intact while you inspect the API.
