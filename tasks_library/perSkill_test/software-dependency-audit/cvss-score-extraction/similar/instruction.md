Review the dependency findings in `/root/data/findings.json` and choose the correct CVSS score for each record.

Save `/root/similar_cvss_selection.json` as a JSON array with one object per finding.

Each object must contain:
- `package`
- `cve_id`
- `selected_score`
- `selected_source`
- `selected_version`

Use the score priority `NVD v3 -> GHSA v3 -> RedHat v3 -> NVD v2 -> N/A`.
Preserve the input order.
