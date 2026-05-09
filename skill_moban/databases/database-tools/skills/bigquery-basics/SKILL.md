# BigQuery Basics

BigQuery is a serverless, AI-ready data platform that enables high-speed analysis of large datasets using SQL and Python. Its disaggregated architecture separates compute and storage, allowing them to scale independently while providing built-in machine learning, geospatial analysis, and business intelligence capabilities.

## Setup and Basic Usage

1. **Enable the BigQuery API:**  
```bash  
gcloud services enable bigquery.googleapis.com  
```
2. **Create a Dataset:**  
```bash  
bq mk --dataset --location=US my_dataset  
```
3. **Create a Table:**  
Create a file named `schema.json` with your table schema:  
```json  
[  
  {  
    "name": "name",  
    "type": "STRING",  
    "mode": "REQUIRED"  
  },  
  {  
    "name": "post_abbr",  
    "type": "STRING",  
    "mode": "NULLABLE"  
  }  
]  
```  
Then create the table with the `bq` tool:  
```bash  
bq mk --table my_dataset.mytable schema.json  
```
4. **Run a Query:**  
```bash  
bq query --use_legacy_sql=false \  
'SELECT name FROM `bigquery-public-data.usa_names.usa_1910_2013` \  
WHERE state = "TX" LIMIT 10'  
```

## Reference Directory

* [Core Concepts](https://github.com/google/skills/blob/HEAD/skills/cloud/bigquery-basics/references/core-concepts.md): Storage types, analytics workflows, and BigQuery Studio features.
* [CLI Usage](https://github.com/google/skills/blob/HEAD/skills/cloud/bigquery-basics/references/cli-usage.md): Essential `bq` command-line tool operations for managing data and jobs.
* [Client Libraries](https://github.com/google/skills/blob/HEAD/skills/cloud/bigquery-basics/references/client-library-usage.md): Using Google Cloud client libraries for Python, Java, Node.js, and Go.
* [MCP Usage](https://github.com/google/skills/blob/HEAD/skills/cloud/bigquery-basics/references/mcp-usage.md): Using the BigQuery remote MCP server and Gemini CLI extension.
* [Infrastructure as Code](https://github.com/google/skills/blob/HEAD/skills/cloud/bigquery-basics/references/iac-usage.md): Terraform examples for datasets, tables, and reservations.
* [IAM & Security](https://github.com/google/skills/blob/HEAD/skills/cloud/bigquery-basics/references/iam-security.md): Roles, permissions, and data governance best practices.

_If you need product information not found in these references, use the Developer Knowledge MCP server `searchdocuments` tool._

## Related Skills

* [BigQuery AI & ML Skill](https://github.com/google/adk-python/tree/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml): SKILL.md file for BigQuery AI and ML capabilities.
* [BigQuery AI & ML References](https://github.com/google/adk-python/tree/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references): Reference files published for the BigQuery AI and ML skill.  
  * [bigquery\_ai\_classify.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fclassify.md)
  * [bigquery\_ai\_detect\_anomalies.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fdetect%5Fanomalies.md)
  * [bigquery\_ai\_forecast.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fforecast.md)
  * [bigquery\_ai\_generate.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fgenerate.md)
  * [bigquery\_ai\_generate\_bool.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fgenerate%5Fbool.md)
  * [bigquery\_ai\_generate\_double.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fgenerate%5Fdouble.md)
  * [bigquery\_ai\_generate\_int.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fgenerate%5Fint.md)
  * [bigquery\_ai\_if.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fif.md)
  * [bigquery\_ai\_score.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fscore.md)
  * [bigquery\_ai\_search.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fsearch.md)
  * [bigquery\_ai\_similarity.md](https://github.com/google/adk-python/blob/main/src/google/adk/tools/bigquery/skills/bigquery-ai-ml/references/bigquery%5Fai%5Fsimilarity.md)
