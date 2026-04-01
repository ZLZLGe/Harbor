name
universal-eda

description
Comprehensive exploratory data analysis for any dataset type. Use when you need to understand a new dataset before analysis, identify patterns and relationships, check data quality, examine distributions, detect anomalies, or generate insights. Works systematically through data profiling, quality checks, distribution analysis, correlation detection, and visualization. Applicable to time-series, transactional, behavioral, operational, and analytical datasets.

Universal EDA

Systematic exploratory data analysis that works for any dataset. Balances thoroughness with efficiency by adapting depth to dataset complexity.

Quick Decision Tree

Start here based on user's request:

"Analyze this dataset" → Full workflow (all 5 phases)

"Check data quality" → Phase 1 only, then ask if they want more

"Show me distributions/patterns" → Phase 1 (brief) + Phase 3-4

"Find correlations/relationships" → Phase 1 (brief) + Phase 4

"Why is [metric] behaving this way?" → Targeted investigation (see Phase 5)

Core Workflow

Execute in this order, pausing for user confirmation after each phase:

Phase 1: Data Profile & Quality (ALWAYS DO THIS FIRST)

Purpose: Understand structure and identify quality issues before analysis.

0]}")">import pandas as pd
import numpy as np

# Load and profile
df = pd.read_csv('data.csv')
print(f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"Memory: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
print(f"\nColumns:\n{df.dtypes}")

# Quick quality check
print(f"\nDuplicates: {df.duplicated().sum():,} ({df.duplicated().sum()/len(df)*100:.1f}%)")
print(f"\nMissing values:\n{df.isnull().sum()[df.isnull().sum() > 0]}")

Decision: Does data need cleaning?

Duplicates >1% → Flag and ask user

Missing >20% in any column → Flag as critical issue

Wrong data types → Fix before proceeding

If clean → Proceed to Phase 2

Checkpoint: Show profile summary, flag issues, get user confirmation.

Phase 2: Column Classification & Context

Purpose: Understand what each column represents and how it should be analyzed.

Auto-classify columns:

# Identify column types
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()

# Detect IDs (high cardinality numeric/string)
id_cols = [col for col in df.columns if df[col].nunique() / len(df) > 0.95]

# Detect constants (zero variance)
constant_cols = [col for col in df.columns if df[col].nunique() <= 1]

# Detect binary flags
binary_cols = [col for col in df.columns if df[col].nunique() == 2]

Present to user:

Column classification (numeric, categorical, date, ID, binary)

Unique value counts

Any ambiguous columns requiring clarification

Checkpoint: Confirm column interpretations. Ask user to clarify business meaning of key columns.

Phase 3: Distribution Analysis

Purpose: Understand value distributions, identify skewness, outliers, and patterns.

Numeric Distributions

# Statistical summary with skewness
numeric_df = df[numeric_cols]
summary = numeric_df.describe().T
summary['skew'] = numeric_df.skew()
summary['kurtosis'] = numeric_df.kurtosis()
print(summary)

# Outlier detection (IQR method)
for col in numeric_cols:
Q1, Q3 = df[col].quantile([0.25, 0.75])
IQR = Q3 - Q1
outliers = ((df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)).sum()
if outliers > 0:
print(f"{col}: {outliers:,} outliers ({outliers/len(df)*100:.1f}%)")

Interpretation rules:

|Skewness| > 1: Highly skewed → Consider log transform

Kurtosis > 3: Heavy tails with outliers

Outliers >10%: Investigate source (data errors vs real variation)

Visualizations:

import matplotlib.pyplot as plt
import seaborn as sns

# Histograms for all numeric columns
numeric_df.hist(bins=30, figsize=(15, 10), edgecolor='black')
plt.tight_layout()
plt.savefig('distributions.png', dpi=300)

# Box plots for outlier visualization
numeric_df.plot(kind='box', subplots=True, layout=(3,3),
figsize=(15, 10), sharex=False)
plt.tight_layout()
plt.savefig('boxplots.png', dpi=300)

Categorical Distributions

95:
print(f"⚠️ Nearly constant: top value = {top_pct:.1f}%")
elif nunique > len(df) * 0.5:
print(f"⚠️ Very high cardinality: may be ID or need grouping")">for col in categorical_cols[:10]:  # Limit to first 10 to avoid spam
nunique = df[col].nunique()
top_val = df[col].value_counts().iloc[0]
top_pct = top_val / len(df) * 100

print(f"\n{col}: {nunique} unique values")
if nunique <= 20:
print(df[col].value_counts().head(10))

if top_pct > 95:
print(f"⚠️ Nearly constant: top value = {top_pct:.1f}%")
elif nunique > len(df) * 0.5:
print(f"⚠️ Very high cardinality: may be ID or need grouping")

Checkpoint: Show distribution summary and visualizations. Flag any highly skewed or problematic distributions.

Phase 4: Correlation & Relationship Analysis

Purpose: Identify relationships between variables that inform analysis or modeling.

# Correlation matrix (numeric only)
corr_matrix = numeric_df.corr()

# Find high correlations
high_corr = []
for i in range(len(corr_matrix.columns)):
for j in range(i+1, len(corr_matrix.columns)):
if abs(corr_matrix.iloc[i, j]) >= 0.7:
high_corr.append({
'var1': corr_matrix.columns[i],
'var2': corr_matrix.columns[j],
'corr': corr_matrix.iloc[i, j]
})

print("High correlations (|r| ≥ 0.7):")
for item in high_corr:
print(f"{item['var1']} ↔ {item['var2']}: {item['corr']:.3f}")

# Heatmap
plt.figure(figsize=(12, 10))
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm',
center=0, square=True, linewidths=1, cbar_kws={"shrink": 0.8})
plt.title('Correlation Matrix', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('correlation_heatmap.png', dpi=300)

Interpretation:

|r| > 0.9: Strong multicollinearity → Consider removing one variable

0.7 < |r| < 0.9: Moderate correlation → Investigate relationship

Negative correlations: Important inverse relationships

For categorical relationships:

# Chi-square test for categorical independence
from scipy.stats import chi2_contingency

for cat1 in categorical_cols[:5]:
for cat2 in categorical_cols[:5]:
if cat1 < cat2:  # Avoid duplicates
contingency = pd.crosstab(df[cat1], df[cat2])
chi2, p_value, dof, expected = chi2_contingency(contingency)
if p_value < 0.05:
print(f"{cat1} × {cat2}: p={p_value:.4f} (dependent)")

Checkpoint: Show correlation findings and relationships. Discuss implications for analysis.

Phase 5: Pattern Detection & Insights

Purpose: Surface actionable insights based on the analysis.

Adapt based on dataset type:

Time Series Data (has date column)

0 else 'Decreasing'}, R²={r_value**2:.3f}")

# Seasonality check (day of week pattern)
df['weekday'] = df['date'].dt.day_name()
weekly_pattern = df.groupby('weekday')['metric'].mean()
print("\nWeekday pattern:\n", weekly_pattern.sort_values(ascending=False))"># Time-based aggregation
df['date'] = pd.to_datetime(df['date'])
daily = df.groupby(df['date'].dt.date).agg({
'metric': ['sum', 'mean', 'count']
})

# Trend detection
from scipy import stats
x = np.arange(len(daily))
slope, intercept, r_value, p_value, std_err = stats.linregress(x, daily['metric']['mean'])
print(f"Trend: {'Increasing' if slope > 0 else 'Decreasing'}, R²={r_value**2:.3f}")

# Seasonality check (day of week pattern)
df['weekday'] = df['date'].dt.day_name()
weekly_pattern = df.groupby('weekday')['metric'].mean()
print("\nWeekday pattern:\n", weekly_pattern.sort_values(ascending=False))

Segmentation Data (has group/category columns)

# Compare segments
for segment_col in categorical_cols:
if df[segment_col].nunique() < 20:  # Manageable number of segments
segment_stats = df.groupby(segment_col)['target_metric'].agg([
'count', 'mean', 'std', 'median'
]).sort_values('mean', ascending=False)
print(f"\n{segment_col} performance:\n{segment_stats}")

Behavioral Data (has user/customer actions)

# User-level aggregation
user_behavior = df.groupby('user_id').agg({
'event': 'count',
'revenue': 'sum',
'date': ['min', 'max']
})
user_behavior.columns = ['event_count', 'total_revenue', 'first_seen', 'last_seen']
print(user_behavior.describe())

Checkpoint: Present insights discovered. Ask user which patterns to investigate deeper.

Visualization Best Practices

Always create:

Distributions - Histograms + box plots for numeric columns

Correlations - Heatmap for numeric relationships

Key metrics - Bar/line charts for top-level insights

Visual standards:

# Set consistent style
sns.set_style("whitegrid")
sns.set_palette("husl")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'

# Use clear titles and labels
plt.title('Distribution of Revenue', fontsize=14, fontweight='bold')
plt.xlabel('Revenue ($)', fontsize=12)
plt.ylabel('Frequency', fontsize=12)

# Save all charts
plt.savefig('chart_name.png', dpi=300, bbox_inches='tight', facecolor='white')

Quality Flags & Thresholds

Automatically flag these issues:

Issue
Threshold
Severity
Action

Duplicates
>5%
HIGH
Investigate and deduplicate

Missing values
>30%
HIGH
Flag column as unreliable

Missing values
10-30%
MEDIUM
Decide imputation strategy

Missing values
<10%
LOW
Drop or impute

Outliers
>10%
MEDIUM
Investigate source

Skewness
|skew| > 2
MEDIUM
Consider transformation

Constant column
>95% same value
LOW
Drop from analysis

High cardinality
>50% unique
LOW
May need grouping

Adaptive Depth

Adjust thoroughness based on:

Small dataset (<10k rows): Full analysis, show all details
Medium dataset (10k-1M rows): Summarize, show top 10 of each analysis
Large dataset (>1M rows): Sample for distribution analysis, aggregate for patterns

# Adaptive sampling
if len(df) > 1_000_000:
sample_size = min(100_000, len(df))
df_sample = df.sample(sample_size, random_state=42)
print(f"Using sample of {sample_size:,} rows for distribution analysis")
else:
df_sample = df

Integration with Other Skills

When to use specialized skills:

Data quality issues found → Use data-qa skill for comprehensive audit

SaaS metrics present → Use saas-eda skill for subscription analysis

Need structured QA report → Use data-qa skill to generate formal report

This skill focuses on exploration and pattern detection; use specialized skills for domain-specific analysis or formal quality reporting.

Common Patterns

Pattern 1: Initial exploration
User: "Analyze this dataset" → Full workflow (5 phases) → Present findings → User asks follow-up

Pattern 2: Targeted investigation
User: "Why is revenue dropping?" → Phase 1 (brief) → Phase 5 (time series focus) → Deep dive on specific pattern

Pattern 3: Pre-modeling prep
User: "Prepare data for modeling" → Phase 1-4 → Identify issues → Recommend transformations → Validate

Pattern 4: Data quality check
User: "Is this data clean?" → Phase 1 (comprehensive) → Flag all issues → Stop or continue based on severity

Key Reminders

Always start with Phase 1 - Don't analyze without profiling first

Pause after each phase - Get user confirmation before proceeding

Visualize everything - Charts reveal patterns statistics miss

Flag issues immediately - Don't continue analysis on dirty data

Adapt to context - Match depth to dataset size and user needs

Focus on actionable insights - Every analysis should inform a decision