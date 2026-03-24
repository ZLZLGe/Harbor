---
name: fuzzy-name-search
description: This skill provides lightweight fuzzy search helpers for resolving messy provider names and drug names to standard records.
---

## Overview

This skill is a small search utility for cases where the dataset contains abbreviations, misspellings, or aliases. It ranks candidate records with fuzzy string scoring so you can quickly map raw labels to standard provider IDs or drug codes.

## Usage

### Search a provider using a messy hospital name

```bash
python3 scripts/search_provider.py --keywords "st mary med ctr westlk" --topk 5
```

Example output:

```
** Rank 1 (score = 85.5) **
  provider_id: PRV-1001
  provider_name: Saint Mary Medical Center - Westlake
  network_id: NET-ALPHA
  network_name: NorthEast Care Alliance
```

### Search a drug using a messy drug name

```bash
python3 scripts/search_drug.py --keywords "nivolimab" --topk 5
```

Example output:

```
** Rank 1 (score = 90.0) **
  drug_code: DRUG-9299
  canonical_name: nivolumab 40 mg/4 mL
  brand_name: Opdivo
```

Both scripts default to the CSV assets in `/root`, and support overriding the input path with `--input`.
If you want exact-record lookup after identifying an ID, load the CSV with pandas and filter on the resolved key.
