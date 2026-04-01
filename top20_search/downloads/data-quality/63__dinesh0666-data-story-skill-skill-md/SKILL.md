name
datastory

description
Auto-generates an executive data narrative report from any uploaded CSV or Excel file. Use this skill whenever a user uploads a CSV, XLSX, or data file and wants analysis, a data story, a data profile, a summary report, insights, anomaly detection, or an executive summary of their data. Also trigger when user says things like "analyze this data", "what does this dataset say", "generate a report from this file", "profile my data", "summarize this spreadsheet", "turn this into a story", or "data story". The output is a polished Word document (.docx) with a full data profile, key metrics, anomaly callouts, trend insights, and an AI-written executive narrative — zero manual effort.

DataStory — Auto Data Profiler + Narrative Generator

Given any CSV or Excel file, this skill profiles the data, generates an AI narrative via the
Anthropic API, and outputs a polished .docx executive report. No manual analysis required.

Scripts

Script
Purpose

scripts/profile_data.py
Profiles a CSV/XLSX file → outputs JSON stats

scripts/generate_report.js
Takes profile + narrative JSON → outputs .docx

scripts/run_datastory.sh
Full orchestrator: profile → narrative → docx

Quick Run (full pipeline)

export ANTHROPIC_API_KEY=sk-ant-...
bash scripts/run_datastory.sh mydata.csv
# Output: datastory_mydata.docx

Step-by-step workflow

Step 1 — Profile the data

python3 scripts/profile_data.py <filepath> [--max-rows 10000] > profile.json

Outputs JSON with:

shape — rows x columns

missing_summary — total missing cells and %

columns[] — per-column: dtype, null %, unique count, and either numeric stats or top_values or datetime range

sample_rows — first 5 rows

Edge cases:

Files >10k rows are sampled automatically

CSV encoding failures fall back to latin-1

Step 2 — Generate narrative via Anthropic API

Call claude-sonnet-4-20250514 with max_tokens: 4000.

System prompt: instruct the model to return ONLY JSON with keys:
executive_summary, dataset_overview, key_findings (array of 5), anomalies (array),
column_insights (array of {column, insight}), data_quality_score (int 0-100),
data_quality_label (Poor/Fair/Good/Excellent), data_quality_assessment,
recommended_next_steps (array of 3).

Slim the profile before sending: keep only 3 sample rows and 3 top_values per column.
Parse: strip markdown fences, JSON.parse. On failure, extract first {...} block with regex.

Step 3 — Generate .docx report

node scripts/generate_report.js payload.json [output.docx]

payload.json format: { "profile": {...}, "narrative": {...}, "filename": "myfile.csv" }

Report sections:

Cover — title, filename, date

Executive Summary — callout box + dataset overview

Dataset Overview — stats table

Key Findings — numbered list

Anomalies & Concerns — amber callout (skipped if empty)

Column Profiles — full table with name, type, nulls, stats, outliers

Column Insights — bulleted insights

Data Quality Assessment — score + paragraph

Recommended Next Steps — numbered list

Appendix: Sample Data — first 5 rows

docx rules: WidthType.DXA only, dual widths on tables, ShadingType.CLEAR, no unicode bullets,
no backslash-n in text, outlineLevel on headings for TOC.

Step 4 — Deliver

Copy to /mnt/user-data/outputs/ and call present_files.
Name: datastory_.docx

Error handling

Situation
Action

ANTHROPIC_API_KEY not set
Skip narrative, insert placeholder text

pandas missing
Auto-install via pip

docx npm package missing
Auto-install via npm

JSON parse failure
Strip fences, extract first {...} block

File >100k rows
Sample 10k rows

React Artifact

../app/DataStory.jsx runs this entire pipeline in-browser via the Anthropic API
(Claude-in-Claude pattern). Upload a file, get a full interactive report instantly.