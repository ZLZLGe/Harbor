# Deployment Contract

This project simulates an Azure Container Apps rollout inside one container.

## Required behavior

- The control plane reads `infra/containerapp.template.json` and deploys one public API revision.
- The public revision is considered healthy only when the configured readiness path succeeds.
- Public ingress must continue to serve:
  - `GET /healthz`
  - `GET /api/v1/rollouts/summary?region=<slug>&service=<slug>`
  - `GET /api/v1/rollouts/incidents?region=<slug>&service=<slug>`
- The public API must read incident data from the mirror service using the configured managed-identity style headers.
- The local fallback file is diagnostic-only. It is not an acceptable steady-state data source for public responses.
- For supported region/service combinations, the public `summary` and `incidents` responses must stay internally consistent with each other and with the mirrored feed.
