---
name: data-quality-frameworks
description: Implement data quality validation with Great Expectations, dbt tests, and data contracts.
---

# Data Quality Frameworks

Use this skill when building data quality pipelines, defining validation rules, and enforcing schema expectations.

## Instructions

- Identify the critical datasets and schema constraints for each table.
- Define Great Expectations suites and dbt tests for null checks, uniqueness checks, and range checks.
- Configure checkpoints so the same validation runs in CI/CD for every dataset refresh.
- Store the expectation suite, datasource settings, and test configuration in versioned files.
- Fail the pipeline automatically when validation checks exceed the allowed threshold.

## Notes

- Prefer deterministic validation over exploratory analysis.
- Keep the checks reproducible across local and CI runs.
