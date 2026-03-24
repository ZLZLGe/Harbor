# Transfer: Async Endpoint Audit with Bounded Concurrency

In `/root/workspace/`, there is a sequential Python auditor for local HTTP endpoints. It probes each endpoint one by one, records the observed status code and latency, and validates JSON payloads against required fields and expected values.

You need to convert this workflow into a bounded-concurrency asynchronous auditor while preserving input order and detailed failure reporting.

Write your solution in `/root/workspace/async_endpoint_audit.py` and implement these functions:

1. `async def audit_endpoints_async(targets, concurrency=8)`
   - Return an `AuditRun`
   - Preserve the input order of `targets`
   - Never exceed the requested concurrency while requests are in flight
   - Keep the same `EndpointTarget`, `AuditResult`, and `AuditRun` data model used by the provided baseline files

2. `def build_audit_report(audit_run)`
   - Return a report dictionary that summarizes:
     - counts by observed status code
     - counts by JSON validation outcome
     - latency statistics
     - slowest targets
     - failing targets and reasons

3. `async def run_audit_from_manifest(base_url, manifest_path="/root/workspace/endpoint_manifest.json", concurrency=8)`
   - Load targets from the provided manifest
   - Run the bounded-concurrency audit
   - Return the summary report from `build_audit_report`

Requirements:

- Use `asyncio` for orchestration
- Bound concurrency explicitly instead of launching every request at once
- Reuse the provided helper modules and stay compatible with them
- Keep transport errors and invalid JSON responses in the output instead of dropping them
- Match the sequential baseline on ordering and validation semantics

Performance target with 6 workers on the delayed local test server:

- The asynchronous audit should achieve at least `2.5x` speedup over the sequential baseline

Files already provided in `/root/workspace/`:

- `endpoint_fixture.py`: shared data models, manifest loader, and report helpers
- `endpoint_manifest.json`: deterministic endpoint definitions for manifest-driven runs
- `sequential_endpoint_audit.py`: sequential baseline implementation

Your implementation must stay compatible with those files.
