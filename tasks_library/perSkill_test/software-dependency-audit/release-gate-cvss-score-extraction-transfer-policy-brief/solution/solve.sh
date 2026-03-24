#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
import os


SNAPSHOT_PATH = os.environ.get(
    "RELEASE_CANDIDATE_SNAPSHOT_PATH", "/root/release_candidate_snapshot.json"
)
POLICY_PATH = os.environ.get("RELEASE_GATE_POLICY_PATH", "/root/release_gate_policy.json")
OUTPUT_PATH = os.environ.get("RELEASE_GATE_BRIEF_PATH", "/root/release_gate_brief.md")


def choose_score(cvss):
    for source_key, label in (
        ("nvd", "NVD"),
        ("ghsa", "GHSA"),
        ("redhat", "RedHat"),
    ):
        source_data = cvss.get(source_key, {})
        score = source_data.get("v3_score")
        if score is not None:
            return float(score), label
    return None, "N/A"


with open(SNAPSHOT_PATH, "r", encoding="utf-8") as handle:
    snapshot = json.load(handle)

with open(POLICY_PATH, "r", encoding="utf-8") as handle:
    policy = json.load(handle)

rows = []
for component_entry in snapshot["components"]:
    component = component_entry["component"]
    artifact = component_entry["artifact"]
    for advisory in component_entry.get("advisories", []):
        score, source = choose_score(advisory.get("cvss", {}))
        fixed_version = advisory.get("fixed_version") or "N/A"
        rows.append(
            {
                "Component": component,
                "Artifact": artifact,
                "Advisory_ID": advisory["advisory_id"],
                "Package": advisory["package"],
                "Selected_CVSS": score,
                "Selected_CVSS_Text": "N/A" if score is None else f"{score:.1f}",
                "Score_Source": source,
                "Fixed_Version": fixed_version,
                "Reference_URL": advisory["reference_url"],
            }
        )

rows.sort(
    key=lambda item: (
        item["Selected_CVSS"] is None,
        -(item["Selected_CVSS"] or 0.0),
        item["Advisory_ID"],
    )
)

high_risk_floor = float(policy["high_risk_score_floor"])
block_score = float(policy["block_if_any_score_at_least"])
block_count = int(policy["block_if_high_risk_count_at_least"])

scored_count = sum(1 for row in rows if row["Selected_CVSS"] is not None)
high_risk_count = sum(
    1 for row in rows if row["Selected_CVSS"] is not None and row["Selected_CVSS"] >= high_risk_floor
)
unscored_count = len(rows) - scored_count
has_single_blocker = any(
    row["Selected_CVSS"] is not None and row["Selected_CVSS"] >= block_score for row in rows
)
threshold_triggered = has_single_blocker or high_risk_count >= block_count
decision = "BLOCK" if threshold_triggered else "PASS"
trigger_flag = "YES" if threshold_triggered else "NO"
trigger_reason = (
    f"Single-advisory block threshold ({block_score:.1f}) "
    f"{'is met' if has_single_blocker else 'is not met'}; "
    f"{high_risk_count} advisories meet or exceed {high_risk_floor:.1f}, "
    f"which {'meets' if high_risk_count >= block_count else 'does not meet'} "
    f"the block-count threshold of {block_count}."
)

lines = [
    "# Release Gate Brief",
    "",
    f"- Release ID: {snapshot['release_id']}",
    f"- Service: {snapshot['service']}",
    f"- Planned Release Date: {snapshot['planned_release_date']}",
    f"- Policy: {policy['policy_name']} ({policy['policy_version']})",
    "",
    "## Gate Decision",
    f"- Decision: {decision}",
    f"- Blocking Threshold Triggered: {trigger_flag}",
    f"- Trigger Reason: {trigger_reason}",
    "",
    "## Risk Summary",
    f"- Advisories Reviewed: {len(rows)}",
    f"- Advisories With Selected Scores: {scored_count}",
    f"- High-Risk Advisories (>= {high_risk_floor:.1f}): {high_risk_count}",
    f"- Unscored Advisories: {unscored_count}",
    "",
    "## Selected Advisory Scores",
    "| Component | Artifact | Advisory_ID | Package | Selected_CVSS | Score_Source | Fixed_Version | Reference_URL |",
    "| --- | --- | --- | --- | --- | --- | --- | --- |",
]

for row in rows:
    lines.append(
        "| {Component} | {Artifact} | {Advisory_ID} | {Package} | {Selected_CVSS_Text} | {Score_Source} | {Fixed_Version} | {Reference_URL} |".format(
            **row
        )
    )

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    handle.write("\n".join(lines) + "\n")
PY
