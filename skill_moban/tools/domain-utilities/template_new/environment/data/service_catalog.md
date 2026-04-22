# Local Service Catalog

Base URL: `http://127.0.0.1:8331`

Available endpoints:

- `GET /health`
  - returns service health.
- `GET /manifest`
  - returns the segment slug, supported endpoints, and candidate domains known to the local snapshot service.
- `GET /snapshots/<domain>`
  - returns the frozen RDAP, DNS, and listing snapshot for one candidate domain.

Notes:

- The service is local-only and deterministic.
- The service mirrors data that a domain research workflow would usually gather from RDAP, registrar inventory, and DNS checks, but the responses are frozen for reproducibility.
- The raw per-domain snapshot payloads are not part of the visible task input files; use the documented endpoint instead.
- Do not assume the service covers every scoring field; it is one source in a larger evidence chain.
