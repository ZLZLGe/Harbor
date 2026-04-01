# Data Quality Audit

The primary goal of this bundle is data objective clarity, with success criteria laid out before each check. The schema scope is strictly limited to the production tables, and each column definition links back to tangible business rules that the data engineering team owns.

## Environment

Every run depends on deterministic configuration files and explicitly specified resources such as dataset connection strings, sample staging tables, and storage credentials.

## Verification

Explicit thresholds separate healthy from unhealthy metrics, and automated checks are wired to the nightly scheduler so verification stays repeatable.
