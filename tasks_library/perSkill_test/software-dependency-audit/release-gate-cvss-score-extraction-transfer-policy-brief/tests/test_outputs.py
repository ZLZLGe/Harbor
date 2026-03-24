import os


EXPECTED_MARKDOWN = """# Release Gate Brief

- Release ID: harbor-2026.03-rc2
- Service: payments-control-plane
- Planned Release Date: 2026-03-24
- Policy: Payments Release Gate Policy (2026.03)

## Gate Decision
- Decision: PASS
- Blocking Threshold Triggered: NO
- Trigger Reason: Single-advisory block threshold (9.0) is not met; 2 advisories meet or exceed 7.0, which does not meet the block-count threshold of 3.

## Risk Summary
- Advisories Reviewed: 5
- Advisories With Selected Scores: 4
- High-Risk Advisories (>= 7.0): 2
- Unscored Advisories: 1

## Selected Advisory Scores
| Component | Artifact | Advisory_ID | Package | Selected_CVSS | Score_Source | Fixed_Version | Reference_URL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| billing-worker | registry.harbor.example/payments/billing-worker:2026.03-rc2 | GHSA-7f9m-r47m-63cc | fast-json-stringify | 8.1 | GHSA | 5.16.1 | https://github.com/advisories/GHSA-7f9m-r47m-63cc |
| billing-worker | registry.harbor.example/payments/billing-worker:2026.03-rc2 | CVE-2026-31003 | libxml2 | 7.4 | RedHat | 2.11.9 | https://access.redhat.com/security/cve/CVE-2026-31003 |
| edge-api | registry.harbor.example/payments/edge-api:2026.03-rc2 | CVE-2026-31001 | hypercorn | 6.8 | NVD | 0.17.4 | https://nvd.nist.gov/vuln/detail/CVE-2026-31001 |
| edge-api | registry.harbor.example/payments/edge-api:2026.03-rc2 | CVE-2026-31004 | pyjwt | 5.9 | NVD | 2.10.0 | https://nvd.nist.gov/vuln/detail/CVE-2026-31004 |
| release-ui | registry.harbor.example/payments/release-ui:2026.03-rc2 | GHSA-2m39-px67-4p8j | serialize-javascript | N/A | N/A | N/A | https://github.com/advisories/GHSA-2m39-px67-4p8j |
"""


def normalize_markdown(text):
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def get_output_path():
    candidates = [
        os.environ.get("RELEASE_GATE_BRIEF_PATH"),
        "/root/release_gate_brief.md",
        "release_gate_brief.md",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    raise FileNotFoundError("release_gate_brief.md not found")


def test_release_gate_brief_matches_expected():
    path = get_output_path()
    with open(path, "r", encoding="utf-8") as handle:
        actual = handle.read()

    assert normalize_markdown(actual) == normalize_markdown(
        EXPECTED_MARKDOWN
    ), "Markdown brief does not match expected release gate decision"
