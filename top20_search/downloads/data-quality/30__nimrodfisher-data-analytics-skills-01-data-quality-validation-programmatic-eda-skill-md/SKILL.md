---
name: programmatic-eda
description: Systematic exploratory data analysis following best practices. Use when analyzing any dataset to understand structure, identify data quality issues (duplicates, missing values, inconsistencies, outliers), examine distributions, detect correlations, and generate visualizations. Provides comprehensive data profiling with sanity checks before analysis.
---

# Programmatic EDA

## Quick Start

Execute systematic data quality checks, distribution analysis, and correlation detection on any dataset with automated sanity checks.

## Context Requirements

Before starting EDA, Claude needs:

1. **Dataset Access**: The data file or database connection
2. **Business Context**: What this data represents and what decisions it informs
3. **Quality Thresholds** (optional): What % missing/outliers are acceptable

## Context Gathering

### If dataset not yet loaded:
"Please provide your dataset. I can work with:
- CSV/Excel files (upload or provide path)
- Database connection details
- Pandas DataFrame (if already loaded in notebook)"

### If business context missing:
"To provide relevant insights, I need to understand:
1. What does this dataset represent? (customers, transactions, events, etc.)
2. What business question are you trying to answer?
3. What time period does this cover?
4. Are there any known data quality issues I should be aware of?"

### For quality thresholds (if not provided, use defaults):
"I'll use standard thresholds unless you specify otherwise:
- Missing values: Flag if >5% (warn if >30%)
- Outliers: Flag using IQR method (1.5 × IQR)
- Duplicates: Flag if >1%

Do these work for your use case, or should I adjust?"

## Workflow

### 1. Data Loading & Overview