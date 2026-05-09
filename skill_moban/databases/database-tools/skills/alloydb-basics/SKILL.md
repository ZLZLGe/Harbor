# AlloyDB Basics

AlloyDB for PostgreSQL is a managed, PostgreSQL-compatible database service designed for enterprise-grade performance and availability. It utilizes a disaggregated compute and storage architecture to scale resources independently. It also provides AlloyDB AI, a collection of features that includes AI-powered search (vector, hybrid search, and AI functions), natural language capabilities, conversational analytics, and inference features like forecasting and model endpoint management to help developers build AI apps faster.

## Quick Start

1. **Enable the AlloyDB API:**  
```bash  
gcloud services enable alloydb.googleapis.com  
```
2. **Create a Cluster:**  
```bash  
gcloud alloydb clusters create my-cluster --region=us-central1 \
    --password=my-password --network=my-vpc  
```  
_Note: For production, we recommend using IAM database authentication instead of passwords. If passwords must be used, use secure secret management (e.g., Secret Manager) instead of passing passwords in cleartext._
3. **Create a Primary Instance:**  
```bash  
gcloud alloydb instances create my-primary --cluster=my-cluster \
    --region=us-central1 --instance-type=PRIMARY --cpu-count=2  
```

## Reference Directory

* [Core Concepts](https://github.com/google/skills/blob/HEAD/skills/cloud/alloydb-basics/references/core-concepts.md): Architecture, disaggregated storage, and performance features.
* [CLI Usage](https://github.com/google/skills/blob/HEAD/skills/cloud/alloydb-basics/references/cli-usage.md): Essential `gcloud alloydb` commands for cluster and instance management.
* [Client Libraries & Connectors](https://github.com/google/skills/blob/HEAD/skills/cloud/alloydb-basics/references/client-library-usage.md): Connecting to AlloyDB using Python, Java, Node.js, and Go.
* [MCP Usage](https://github.com/google/skills/blob/HEAD/skills/cloud/alloydb-basics/references/mcp-usage.md): Using the AlloyDB remote MCP server and Gemini CLI extension.
* [Infrastructure as Code](https://github.com/google/skills/blob/HEAD/skills/cloud/alloydb-basics/references/iac-usage.md): Terraform configuration and deployment examples.
* [IAM & Security](https://github.com/google/skills/blob/HEAD/skills/cloud/alloydb-basics/references/iam-security.md): Predefined roles, service agents, and database authentication.

_If you need product information not found in these references, use the Developer Knowledge MCP server `searchdocuments` tool._
