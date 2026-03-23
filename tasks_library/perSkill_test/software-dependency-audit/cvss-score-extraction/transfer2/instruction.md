Draft a short provenance brief for the findings in `/root/data/findings.json`.

Save `/root/transfer2_cvss_provenance.md`.

Format:
- start with the title `# CVSS Provenance Brief`
- include one bullet per finding whose chosen score does not come from NVD v3
- each bullet must follow:
  `- <CVE_ID> (<package>): <selected_score> via <selected_source> <selected_version>`

Use the score priority `NVD v3 -> GHSA v3 -> RedHat v3 -> NVD v2 -> N/A`.
Preserve the input order for the included bullets.
