name
review-data-pr

description
Perform an intelligent review of geographic data PRs beyond schema validation. Use this skill whenever reviewing a data PR, performing code review on contributions, checking if data makes geographical sense, or assessing data quality. Trigger on: PR review requests for data changes, "review this PR", "does this look right", "is this data correct", quality assessment requests, geographic plausibility checks, suspicious pattern detection, or any pull request touching files in the contributions/ directory. This goes beyond schema validation to check real-world geographic accuracy.

Review Process

This skill goes beyond schema validation to check data quality and plausibility.

Step 1: Read the PR Context

Read the PR description for intent and data source

Check which files are changed and what entity types are involved

Note the number of records being added/modified/deleted

Step 2: Check Geographical Plausibility

For each record, consider:

Does the city name make sense for this country/state? (e.g., a city named "Springfield" in India would be unusual)

Are the coordinates in the right general area? (a city in Maharashtra should be in western India)

Is the state assignment correct? (verify the city actually belongs to that state)

For states: does the type make sense? (e.g., "province" vs "state" vs "region")

Step 3: Look for Suspicious Patterns

Flag these patterns for manual review:

All records have identical or sequential coordinates (copy-paste error)

All records have the same latitude or longitude (likely placeholder data)

Records have unusually low coordinate precision (e.g., whole numbers like 34.0, -118.0)

Bulk additions with no clear geographic grouping

Names that appear machine-generated or contain unusual characters

Coordinates that resolve to ocean/water bodies rather than land

Step 4: Verify Data Source

Is the data source documented in the PR description?

Is it a Tier 1 (government, ISO, UN) or Tier 2 (GeoNames, academic) source?

Is the source URL accessible?

Does the source actually contain the claimed data?

Step 5: Check for Completeness

For city additions:

Are nearby or related cities included? (not required, but useful context)

Is the timezone field included? (optional but valuable)

Is the wikiDataId included? (optional but aids cross-referencing)

Step 6: Assess Overall Quality

Rate the contribution on:

Accuracy: Do the values appear correct?

Completeness: Are optional but valuable fields included?

Source quality: Is the data from a reliable source?

Impact: How many users would benefit from this data?

Review Output

Structure your review as:

### Data Quality Review

**Plausibility:** [Assessment]
**Source Quality:** [Assessment]
**Completeness:** [Assessment]

**Findings:**
- [List specific observations]

**Recommendation:** [Approve / Request Changes / Needs Maintainer Review]

Escalation Criteria

Escalate to the maintainer (@dr5hn) when:

Contribution involves deletions of states or countries

Data source is questionable or unverifiable

Coordinates appear systematically incorrect

Contribution modifies more than 100 records

You are uncertain about the geographical accuracy

Tone Guidelines

Be welcoming and constructive, especially for first-time contributors

Acknowledge the effort involved in data contributions

Provide specific, actionable feedback

Link to the contribution guidelines when relevant

Thank contributors for their work