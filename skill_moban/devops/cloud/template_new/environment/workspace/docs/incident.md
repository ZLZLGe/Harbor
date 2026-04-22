# Incident Summary

The `rollout-summary-api` release that was prepared for an Azure Container Apps style rollout is stuck in a bad state:

- the new revision does not become healthy through the local control plane
- the public `/api/v1/rollouts/summary` response is stale when operators compare it with the mirror-backed feed
- on-call notes say the service should always read from the mirrored incident feed instead of serving the local fallback cache

Observed symptoms from the last failed rollout:

1. The control plane recorded readiness failures during apply.
2. Operators sometimes saw `snapshot_id = fallback-cache-2026-04-14` instead of the current mirrored snapshot.
3. The latest incident shown for `eastus2/containerapps` was older than the mirror feed even when the API returned HTTP 200 during local debugging.

Business constraints:

- The service must stay deployable through the current Azure Container Apps style template.
- The public API must keep the same endpoints and query parameters.
- The service must continue to use the mirror-backed data path for production responses.
