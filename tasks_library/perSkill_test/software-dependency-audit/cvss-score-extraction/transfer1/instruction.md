The release board wants a gate decision for each dependency advisory in `/root/data/findings.json`.

Save `/root/transfer1_release_gate.csv` with columns:
`Package,CVE_ID,Selected_Score,Selected_Source,Release_Gate`

Rules:
- choose the score using `NVD v3 -> GHSA v3 -> RedHat v3 -> NVD v2 -> N/A`
- `block` for scores >= 9.0
- `review` for scores >= 7.0 and < 9.0
- `monitor` for scores < 7.0
- `manual-review` for `N/A`
- sort by gate priority `block`, `review`, `manual-review`, `monitor`, then by package and CVE ID
