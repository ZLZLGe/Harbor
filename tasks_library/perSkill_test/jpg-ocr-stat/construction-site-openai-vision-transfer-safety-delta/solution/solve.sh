#!/bin/bash

set -euo pipefail

python3 - <<'PY'
from pathlib import Path

rows = [
    ("bay_alpha", 1, 2, 1, 1, "elevated"),
    ("mixing_yard", 2, 1, 1, 2, "critical"),
    ("pump_station", 0, 3, 0, 1, "elevated"),
    ("service_tunnel", 3, 0, 2, 0, "critical"),
    ("west_ramp", 0, 1, 0, 0, "watch"),
]

totals = {
    "missing_guardrails": sum(row[1] for row in rows),
    "removed_warning_cones": sum(row[2] for row in rows),
    "uncovered_holes": sum(row[3] for row in rows),
    "workers_without_helmets": sum(row[4] for row in rows),
}

critical_areas = ", ".join(row[0] for row in rows if row[5] == "critical") or "none"

lines = [
    "# 施工现场安全变化报告",
    "",
    "只统计从 before 到 after 新增或恶化的风险。",
    "",
    "## 区域变化表",
    "| area_id | missing_guardrails | removed_warning_cones | uncovered_holes | workers_without_helmets | risk_level |",
    "| --- | ---: | ---: | ---: | ---: | --- |",
]

for area_id, guardrails, cones, holes, helmets, risk in rows:
    lines.append(
        f"| {area_id} | {guardrails} | {cones} | {holes} | {helmets} | {risk} |"
    )

lines.extend(
    [
        "",
        "## 总计",
        "| metric | count |",
        "| --- | ---: |",
        f"| missing_guardrails | {totals['missing_guardrails']} |",
        f"| removed_warning_cones | {totals['removed_warning_cones']} |",
        f"| uncovered_holes | {totals['uncovered_holes']} |",
        f"| workers_without_helmets | {totals['workers_without_helmets']} |",
        "",
        f"高风险区域: {critical_areas}",
        "",
    ]
)

Path("/app/workspace/site_safety_delta.md").write_text("\n".join(lines), encoding="utf-8")
PY
