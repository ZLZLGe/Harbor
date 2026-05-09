# Google Kubernetes Engine (GKE) Basics

GKE is a managed Kubernetes platform on Google Cloud for deploying, scaling, and operating containerized applications. This skill defaults to the **golden path Autopilot configuration** — see [gke-golden-path.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-golden-path.md) for defaults, rules, and guardrails.

## Quick Start

```bash
gcloud services enable container.googleapis.com
gcloud container clusters create-auto my-cluster --region=us-central1
gcloud container clusters get-credentials my-cluster --region=us-central1
kubectl create deployment hello-server \
  --image=us-docker.pkg.dev/google-samples/containers/gke/hello-app:1.0

```

## Reference Directory

Load the relevant reference based on trigger keywords. Prefer the most specific match; if ambiguous, ask the user to clarify.

| Scenario               | Trigger Keywords                                                                          | Reference                                                                                                                          |
| ---------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Core Concepts          | Autopilot vs Standard, architecture, pricing, what is GKE                                 | [core-concepts.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/core-concepts.md)               |
| Golden Path & Defaults | golden path, Day-0 checklist, production defaults, cluster defaults                       | [gke-golden-path.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-golden-path.md)           |
| Cluster Creation       | create cluster, new cluster, provision GKE                                                | [gke-cluster-creation.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-cluster-creation.md) |
| Networking             | private cluster, VPC, subnet, Gateway API, DNS, ingress, egress, datapath                 | [gke-networking.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-networking.md)             |
| Security & IAM         | Workload Identity, Secret Manager, RBAC, Binary Auth, hardening, audit, gVisor, IAM roles | [gke-security.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-security.md)                 |
| Scaling                | HPA, VPA, autoscaler, autoscaling, NAP, scale pods, scale nodes                           | [gke-scaling.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-scaling.md)                   |
| Compute Classes        | ComputeClass, machine family, Spot fallback, GPU node pool, node selection                | [gke-compute-classes.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-compute-classes.md)   |
| Cost                   | cost, savings, Spot VMs, rightsizing, CUD, optimize spend, budget                         | [gke-cost.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-cost.md)                         |
| AI/ML Inference        | inference, model serving, LLM, GPU, TPU, GIQ, vLLM                                        | [gke-inference.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-inference.md)               |
| Upgrades               | upgrade, maintenance window, release channel, patching, version                           | [gke-upgrades.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-upgrades.md)                 |
| Observability          | monitoring, logging, Prometheus, Grafana, metrics, alerts, dashboards                     | [gke-observability.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-observability.md)       |
| Multi-tenancy          | multi-tenant, namespace isolation, team access, enterprise, RBAC planning                 | [gke-multitenancy.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-multitenancy.md)         |
| Batch & HPC            | batch, HPC, job queue, high performance, MPI, parallel                                    | [gke-batch-hpc.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-batch-hpc.md)               |
| App Onboarding         | containerize, deploy app, Dockerfile, onboard, migrate to GKE                             | [gke-app-onboarding.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-app-onboarding.md)     |
| Backup & DR            | backup, restore, disaster recovery, CMEK                                                  | [gke-backup-dr.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-backup-dr.md)               |
| Storage                | storage, PVC, persistent volume, StorageClass, Filestore, GCS FUSE                        | [gke-storage.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-storage.md)                   |
| Reliability            | PDB, health probe, liveness, readiness, topology spread, graceful shutdown                | [gke-reliability.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-reliability.md)           |
| Client Libraries       | client library, client-go, kubernetes python, kubernetes java, kubernetes SDK             | [client-library-usage.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/client-library-usage.md) |
| Infrastructure as Code | Terraform, IaC, HCL, infrastructure as code                                               | [iac-usage.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/iac-usage.md)                       |
| MCP Server             | MCP tools, MCP server, MCP setup                                                          | [mcp-usage.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/mcp-usage.md)                       |
| CLI / Tools            | gcloud, kubectl, commands, how to                                                         | [cli-reference.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/cli-reference.md)               |
| Production Audit       | production readiness, compliance, golden path check                                       | [gke-cluster-creation.md](https://github.com/google/skills/blob/HEAD/skills/cloud/gke-basics/./references/gke-cluster-creation.md) |

_If you need product information not found in these references, use the Developer Knowledge MCP server `searchdocuments` tool._
