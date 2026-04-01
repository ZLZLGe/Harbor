---
name: exploratory-data-analysis
description: Use when performing initial data exploration on a new dataset, before modeling or feature engineering. Triggers on mentions of "EDA", "explore this data", "data profiling", "what does this dataset look like", "summarize this data", "data quality check", or any new dataset analysis request.
metadata:
  author: Phife
  version: '1.0'
---

# Exploratory Data Analysis (EDA)

## Overview

Every dataset tells a story. EDA is how you read the first chapter before writing the rest. This skill provides a **systematic, repeatable methodology** for initial data exploration that ensures nothing gets missed.

**Core principle:** UNDERSTAND the data completely before any modeling, transformation, or feature engineering. Skipping EDA leads to garbage-in, garbage-out.

**Announce at start:** "I'm using the exploratory-data-analysis skill to systematically explore this dataset."

## When to Use

Use for ANY new dataset encounter:
- Receiving a new CSV, Parquet, Excel, or database table
- Starting a new data science project
- Auditing data quality before a pipeline
- Investigating data drift or anomalies
- Onboarding to an existing dataset you haven't seen before
- Pre-modeling validation

**Use this ESPECIALLY when:**
- The dataset has more than 10 columns
- You don't know the data provenance
- Multiple data sources have been merged
- The data will feed a machine learning model
- Stakeholders need a data quality report

## The EDA Protocol

```
NEVER skip a phase. NEVER jump to modeling without completing EDA.
```

Complete all 7 phases in order. Document findings as you go.

---

## Phase 1: First Contact — Shape & Structure

**Goal:** Understand what you're working with before looking at values.

### Checklist

```python
import pandas as pd
import numpy as np

# Load the data
df = pd.read_csv("data.csv")  # Adjust for your format

# 1.1 — Dimensions
print(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")

# 1.2 — Column inventory
print(df.dtypes)
print(f"\nNumeric columns: {df.select_dtypes(include='number').columns.tolist()}")
print(f"Categorical columns: {df.select_dtypes(include='object').columns.tolist()}")
print(f"Datetime columns: {df.select_dtypes(include='datetime').columns.tolist()}")
print(f"Boolean columns: {df.select_dtypes(include='bool').columns.tolist()}")

# 1.3 — First and last rows (spot encoding issues, headers-as-rows, etc.)
print(df.head(10))
print(df.tail(5))

# 1.4 — Memory footprint
print(f"\nMemory usage: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")

# 1.5 — Index check
print(f"Index type: {type(df.index)}")
print(f"Index is unique: {df.index.is_unique}")
```

### What to Look For
- Mismatched dtypes (numbers stored as strings, dates as objects)
- Column names with spaces, special characters, or inconsistent casing
- Unnamed columns (often from bad CSV exports)
- Suspiciously few or many columns vs. what you expected

### Common Fixes
```python
# Standardize column names
df.columns = df.columns.str.strip().str.lower().str.replace(r'[^\w]', '_', regex=True)

# Fix obvious dtype issues
df['date_col'] = pd.to_datetime(df['date_col'], errors='coerce')
df['numeric_col'] = pd.to_numeric(df['numeric_col'], errors='coerce')
```

---

## Phase 2: Missing Values — The Gaps in the Story

**Goal:** Quantify and characterize what's missing. Missing data is information too.

### Checklist

```python
# 2.1 — Missing value counts
missing = df.isnull().sum()
missing_pct = (missing / len(df) * 100).round(2)
missing_report = pd.DataFrame({
    'missing_count': missing,
    'missing_pct': missing_pct
}).sort_values('missing_pct', ascending=False)
print(missing_report[missing_report['missing_count'] > 0])

# 2.2 — Overall missing rate
total_cells = df.shape[0] * df.shape[1]
total_missing = df.isnull().sum().sum()
print(f"\nOverall: {total_missing:,} / {total_cells:,} cells missing ({total_missing/total_cells*100:.1f}%)")

# 2.3 — Missing value patterns (are the same rows missing across columns?)
# Check if missingness is correlated
missing_cols = df.columns[df.isnull().any()].tolist()
if len(missing_cols) > 1:
    print("\nMissing value correlation matrix:")
    print(df[missing_cols].isnull().corr().round(2))

# 2.4 — Rows with most missing values
row_missing = df.isnull().sum(axis=1)
print(f"\nRows with 50%+ missing: {(row_missing > df.shape[1] * 0.5).sum()}")
```

### Visualization
```python
import matplotlib.pyplot as plt
import seaborn as sns

# Heatmap of missing values
plt.figure(figsize=(12, 6))
sns.heatmap(df.isnull(), cbar=True, yticklabels=False, cmap='viridis')
plt.title('Missing Value Heatmap')
plt.tight_layout()
plt.savefig('eda_missing_values.png', dpi=150)
plt.show()
```

### Key Questions to Answer
- Is the missingness **random** (MCAR), **depends on other columns** (MAR), or **depends on the missing value itself** (MNAR)?
- Are there columns with >50% missing? (Consider dropping)
- Do missing values cluster in specific rows? (Possible data collection issue)

---

## Phase 3: Summary Statistics — The Numbers Tell a Story

**Goal:** Get the statistical fingerprint of every column.

### Checklist

```python
# 3.1 — Numeric summary
print("=== Numeric Columns ===")
print(df.describe().T.round(2))

# 3.2 — Check for suspicious statistics
numeric_cols = df.select_dtypes(include='number').columns
for col in numeric_cols:
    print(f"\n--- {col} ---")
    print(f"  Zeros: {(df[col] == 0).sum()} ({(df[col] == 0).mean()*100:.1f}%)")
    print(f"  Negatives: {(df[col] < 0).sum()}")
    print(f"  Unique values: {df[col].nunique()}")
    print(f"  Skewness: {df[col].skew():.2f}")
    print(f"  Kurtosis: {df[col].kurtosis():.2f}")

# 3.3 — Categorical summary
print("\n=== Categorical Columns ===")
cat_cols = df.select_dtypes(include=['object', 'category']).columns
for col in cat_cols:
    print(f"\n--- {col} ---")
    print(f"  Unique values: {df[col].nunique()}")
    print(f"  Most common: {df[col].mode().iloc[0] if not df[col].mode().empty else 'N/A'}")
    print(f"  Top 5:\n{df[col].value_counts().head()}")

# 3.4 — Cardinality check (high-cardinality categoricals are a red flag)
high_card = [(col, df[col].nunique()) for col in cat_cols if df[col].nunique() > 50]
if high_card:
    print(f"\n⚠️  High-cardinality categoricals: {high_card}")
```

### What to Look For
- **Mean ≈ Median?** If not, the distribution is skewed
- **Min/Max realistic?** Watch for sentinel values (-999, 9999, etc.)
- **Std ≈ 0?** Near-zero variance columns carry no information
- **Skewness > 2?** May need transformation for modeling

---

## Phase 4: Outlier Detection — The Unusual Suspects

**Goal:** Identify values that don't belong or deserve special attention.

### Checklist

```python
# 4.1 — IQR method
def detect_outliers_iqr(df, col):
    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)
    IQR = Q3 - Q1
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    outliers = df[(df[col] < lower) | (df[col] > upper)]
    return len(outliers), lower, upper

print("=== Outlier Detection (IQR Method) ===")
for col in numeric_cols:
    count, lower, upper = detect_outliers_iqr(df, col)
    if count > 0:
        pct = count / len(df) * 100
        print(f"  {col}: {count} outliers ({pct:.1f}%) | bounds: [{lower:.2f}, {upper:.2f}]")

# 4.2 — Z-score method (for approximately normal distributions)
from scipy import stats
print("\n=== Outlier Detection (Z-Score > 3) ===")
for col in numeric_cols:
    z = np.abs(stats.zscore(df[col].dropna()))
    outlier_count = (z > 3).sum()
    if outlier_count > 0:
        print(f"  {col}: {outlier_count} extreme values (|z| > 3)")
```

### Visualization
```python
# Box plots for all numeric columns
n_numeric = len(numeric_cols)
fig, axes = plt.subplots(1, min(n_numeric, 6), figsize=(4 * min(n_numeric, 6), 5))
if n_numeric == 1:
    axes = [axes]
for ax, col in zip(axes, numeric_cols[:6]):
    df.boxplot(column=col, ax=ax)
    ax.set_title(col)
plt.suptitle('Outlier Detection — Box Plots', y=1.02)
plt.tight_layout()
plt.savefig('eda_outliers_boxplots.png', dpi=150)
plt.show()
```

### Decision Framework
| Outlier Type | Action |
|-------------|--------|
| **Data entry error** (e.g., age=999) | Fix or remove |
| **Legitimate extreme** (e.g., billionaire income) | Keep, but consider robust methods |
| **Different population** (e.g., B2B vs B2C) | Segment the data |
| **Measurement error** | Investigate data collection |

---

## Phase 5: Distributions — What Shape Is the Data?

**Goal:** Understand the distributional shape of each variable.

### Visualization

```python
# 5.1 — Histograms for numeric columns
n_cols = len(numeric_cols)
n_rows = (n_cols + 2) // 3
fig, axes = plt.subplots(n_rows, 3, figsize=(15, 4 * n_rows))
axes = axes.flatten() if n_cols > 1 else [axes]

for i, col in enumerate(numeric_cols):
    df[col].hist(bins=50, ax=axes[i], edgecolor='black', alpha=0.7)
    axes[i].set_title(col)
    axes[i].axvline(df[col].mean(), color='red', linestyle='--', label='mean')
    axes[i].axvline(df[col].median(), color='green', linestyle='--', label='median')
    axes[i].legend(fontsize=8)

# Hide empty subplots
for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)

plt.suptitle('Feature Distributions', y=1.02, fontsize=14)
plt.tight_layout()
plt.savefig('eda_distributions.png', dpi=150)
plt.show()

# 5.2 — Bar charts for categorical columns (top categories)
for col in cat_cols:
    plt.figure(figsize=(10, 4))
    df[col].value_counts().head(20).plot(kind='barh')
    plt.title(f'{col} — Top Categories')
    plt.tight_layout()
    plt.savefig(f'eda_barplot_{col}.png', dpi=150)
    plt.show()
```

### What to Look For
- **Bimodal/multimodal?** Might indicate mixed populations
- **Heavy tails?** Consider log transformation
- **Uniform?** May be synthetic or bucketed data
- **Spikes at boundaries?** Possible clipping or capping

---

## Phase 6: Correlations & Relationships — How Things Connect

**Goal:** Discover relationships between variables.

### Checklist

```python
# 6.1 — Correlation matrix (Pearson)
corr = df[numeric_cols].corr()
print("=== High Correlations (|r| > 0.7) ===")
high_corr = []
for i in range(len(corr.columns)):
    for j in range(i + 1, len(corr.columns)):
        if abs(corr.iloc[i, j]) > 0.7:
            high_corr.append((corr.columns[i], corr.columns[j], corr.iloc[i, j]))
            print(f"  {corr.columns[i]} ↔ {corr.columns[j]}: {corr.iloc[i, j]:.3f}")

if not high_corr:
    print("  No pairs with |r| > 0.7")
```

### Visualization
```python
# 6.2 — Correlation heatmap
plt.figure(figsize=(12, 10))
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f', cmap='RdBu_r',
            center=0, vmin=-1, vmax=1, square=True)
plt.title('Feature Correlation Matrix')
plt.tight_layout()
plt.savefig('eda_correlation_matrix.png', dpi=150)
plt.show()

# 6.3 — Scatter matrix for top correlated pairs (if any)
if high_corr:
    cols_of_interest = list(set([c[0] for c in high_corr] + [c[1] for c in high_corr]))[:6]
    pd.plotting.scatter_matrix(df[cols_of_interest], figsize=(12, 12), alpha=0.3)
    plt.suptitle('Scatter Matrix — Highly Correlated Features', y=1.02)
    plt.tight_layout()
    plt.savefig('eda_scatter_matrix.png', dpi=150)
    plt.show()
```

### What to Look For
- **r > 0.9:** Potential multicollinearity — may need to drop one
- **r ≈ 0 but nonlinear relationship:** Use Spearman or mutual information instead
- **Unexpected correlations:** Could indicate data leakage or confounding

---

## Phase 7: Target Variable Analysis (If Applicable)

**Goal:** If there's a target/label column, understand its relationship to features.

### Checklist

```python
# 7.1 — Target distribution
target_col = 'target'  # Adjust to your target column name

if df[target_col].dtype in ['object', 'category', 'bool']:
    # Classification target
    print("=== Target Distribution (Classification) ===")
    print(df[target_col].value_counts())
    print(f"\nClass balance ratio: {df[target_col].value_counts().min() / df[target_col].value_counts().max():.2f}")

    # Feature distributions by target class
    for col in numeric_cols:
        if col != target_col:
            print(f"\n--- {col} by {target_col} ---")
            print(df.groupby(target_col)[col].describe().round(2))
else:
    # Regression target
    print("=== Target Distribution (Regression) ===")
    print(df[target_col].describe())
    print(f"Skewness: {df[target_col].skew():.2f}")

    # Correlations with target
    print(f"\n=== Feature Correlations with {target_col} ===")
    target_corr = df[numeric_cols].corr()[target_col].drop(target_col).sort_values(key=abs, ascending=False)
    print(target_corr.round(3))
```

---

## EDA Report Template

After completing all phases, produce a summary report:

```markdown
# EDA Report: [Dataset Name]

**Date:** YYYY-MM-DD
**Analyst:** [Name]
**Dataset:** [Source/Description]

## Dataset Overview
- **Rows:** X | **Columns:** Y
- **Memory:** X MB
- **Time period:** [if applicable]

## Key Findings

### Data Quality
- Missing values: X% overall
- Columns with >20% missing: [list]
- Data type issues found: [list]

### Statistical Summary
- Highly skewed features: [list]
- Near-zero variance features: [list]
- High-cardinality categoricals: [list]

### Outliers
- Columns with significant outliers: [list]
- Recommended action: [keep/cap/remove/investigate]

### Relationships
- Highly correlated pairs (|r|>0.7): [list]
- Potential data leakage: [yes/no, details]

### Target Variable [if applicable]
- Type: Classification/Regression
- Class balance: [balanced/imbalanced, ratio]
- Top predictive features: [list]

## Recommendations
1. [Specific action items]
2. [Data cleaning steps needed]
3. [Feature engineering opportunities]
4. [Modeling considerations]

## Generated Artifacts
- `eda_missing_values.png`
- `eda_outliers_boxplots.png`
- `eda_distributions.png`
- `eda_correlation_matrix.png`
- `eda_scatter_matrix.png`
```

---

## Quick Reference: One-Liner Checks

```python
# Shape at a glance
df.shape, df.dtypes.value_counts(), df.isnull().sum().sum()

# Duplicates
print(f"Duplicate rows: {df.duplicated().sum()}")

# Constant columns (useless features)
constant_cols = [col for col in df.columns if df[col].nunique() <= 1]

# Highly correlated pairs
corr_matrix = df.select_dtypes('number').corr().abs()
upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
to_drop = [col for col in upper.columns if any(upper[col] > 0.95)]
```

## Tool Preferences

- **Python:** pandas, numpy, scipy, matplotlib, seaborn
- **For large datasets (>1M rows):** Consider polars or dask
- **Interactive exploration:** Use Jupyter notebooks when available
- **Automated profiling:** ydata-profiling (formerly pandas-profiling) for a quick comprehensive report

## Anti-Patterns — Don't Do This

| ❌ Anti-Pattern | ✅ Do This Instead |
|----------------|-------------------|
| Jump straight to modeling | Complete all 7 EDA phases |
| Ignore missing values | Quantify, characterize, and decide strategy |
| Assume data types are correct | Verify and fix dtypes in Phase 1 |
| Only look at means | Check median, skewness, distributions |
| Drop outliers without investigation | Understand WHY they're outliers first |
| Visualize without saving | Save all plots as artifacts |
| Skip target analysis | Always analyze the target if one exists |
