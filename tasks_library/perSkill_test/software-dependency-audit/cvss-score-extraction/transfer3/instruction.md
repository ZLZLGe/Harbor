Build a package-level risk matrix from the findings in `/root/data/findings.json`.

Save `/root/transfer3_package_matrix.tsv` as a tab-separated file with columns:
`Package`, `Max_Score`, `Selected_Source`, `Blocking_CVEs`

Rules:
- choose each advisory score using `NVD v3 -> GHSA v3 -> RedHat v3 -> NVD v2 -> N/A`
- `Max_Score` is the highest chosen score for the package
- `Selected_Source` must correspond to that highest score
- `Blocking_CVEs` counts advisories for that package whose chosen score is at least 8.5
- sort by `Max_Score` descending, treating `N/A` as lower than any numeric score, then by package
