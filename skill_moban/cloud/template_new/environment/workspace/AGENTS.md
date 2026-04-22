# Workspace Notes

- The public API lives in `rollout-api/`.
- The deployment template lives in `infra/containerapp.template.json`.
- The local control plane is available at `http://127.0.0.1:8300/__control/...`.
- The public ingress is also exposed at `http://127.0.0.1:8300/`.
- The hidden mirror service and local control plane are diagnostics targets exposed over localhost only; treat them as callable infrastructure, not readable workspace source.
