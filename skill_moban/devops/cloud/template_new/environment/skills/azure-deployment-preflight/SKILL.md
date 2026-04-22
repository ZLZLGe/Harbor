---
name: azure-deployment-preflight
description: Run preflight validation on Azure Container Apps style deployment templates before deployment, then inspect revision health and prove the public API still uses the real downstream mirror chain instead of fallback data.
---

# Azure Deployment Preflight

Use this skill when a task involves:

- Azure deployment templates
- Azure Container Apps style `targetPort`, `secretRef`, readiness, or ingress issues
- Local cloud-control-plane simulations that expose revision apply / health events
- Verifying that a public API still uses the real downstream service after the revision turns healthy

## Workflow

1. Run the static preflight first:

```bash
python /logs/agent/skills/azure-deployment-preflight/scripts/run_local_preflight.py
```

2. Reset and apply the current revision, then inspect health:

```bash
python /logs/agent/skills/azure-deployment-preflight/scripts/redeploy_and_probe.py
python /logs/agent/skills/azure-deployment-preflight/scripts/inspect_control_plane.py
```

3. Once the revision is healthy, sweep the bundled public contract matrix instead of checking only the main symptom:

```bash
python /logs/agent/skills/azure-deployment-preflight/scripts/run_contract_matrix.py
```

4. Verify public data is real mirror data and not fallback:

```bash
python /logs/agent/skills/azure-deployment-preflight/scripts/inspect_mirror_audit.py
```

## Invariants

- Do not modify `/services/control-plane/` or `/services/mirror-service/`.
- Do not replace live mirror calls with the fallback cache.
- Do not remove `secretRef`, ingress, or readiness semantics to make the simulator “look green”.
- A correct fix must satisfy both:
  - the deployed revision becomes healthy
  - public responses stay internally consistent across the summary/incidents contract matrix
  - public responses use the mirrored snapshot and leave mirror audit evidence
