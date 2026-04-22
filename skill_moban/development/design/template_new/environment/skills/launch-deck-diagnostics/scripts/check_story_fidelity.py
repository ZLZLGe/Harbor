#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from common import load_soup


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/app"))
WORKSPACE_ROOT = TASK_ROOT / "workspace"


def load_weekly_kpis() -> list[dict[str, str]]:
    with (WORKSPACE_ROOT / "data" / "weekly_kpis.csv").open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_feature_matrix() -> list[dict[str, str]]:
    with (WORKSPACE_ROOT / "data" / "feature_matrix.csv").open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_quotes() -> list[dict[str, str]]:
    return json.loads((WORKSPACE_ROOT / "data" / "customer_quotes.json").read_text(encoding="utf-8"))


def load_journey() -> dict[str, object]:
    return json.loads((WORKSPACE_ROOT / "data" / "user_journey.json").read_text(encoding="utf-8"))


def main() -> None:
    soup = load_soup()
    failures: list[str] = []

    kpi_slide = soup.select_one('[data-slide-role="kpi-overview"]')
    if kpi_slide is None:
        failures.append("missing kpi-overview slide")
    else:
        expected_rows = load_weekly_kpis()
        expected_chart = {
            (row["week_start"], "median_approval_hours", row["median_approval_hours"])
            for row in expected_rows
        }
        observed_chart = {
            (
                node.get("data-chart-week", "").strip(),
                node.get("data-chart-metric", "").strip(),
                node.get("data-chart-value", "").strip(),
            )
            for node in kpi_slide.select("[data-chart-week][data-chart-metric][data-chart-value]")
        }
        missing_chart = expected_chart - observed_chart
        if missing_chart:
            failures.append("KPI chart does not cover the frozen weekly KPI rows")

    comparison_slide = soup.select_one('[data-slide-role="comparison"]')
    if comparison_slide is None:
        failures.append("missing comparison slide")
    else:
        expected_capabilities = {row["capability"] for row in load_feature_matrix()}
        observed_capabilities = {
            row.get("data-capability", "").strip()
            for row in comparison_slide.select("[data-capability]")
            if row.get("data-capability", "").strip()
        }
        missing_capabilities = expected_capabilities - observed_capabilities
        if missing_capabilities:
            failures.append("comparison slide is missing capability rows from the frozen matrix")

    quotes = {quote["quote_id"] for quote in load_quotes()}
    for role, required_ids in {
        "cover": {"q3"},
        "evidence": {"q1", "q2"},
        "journey-diagram": {"q5"},
        "risks-next-steps": {"q4"},
    }.items():
        slide = soup.select_one(f'[data-slide-role="{role}"]')
        if slide is None:
            failures.append(f"missing {role} slide")
            continue
        observed_ids = {
            node.get("data-quote-id", "").strip()
            for node in slide.select("[data-quote-id]")
            if node.get("data-quote-id", "").strip()
        }
        if not required_ids.issubset(observed_ids):
            failures.append(f"{role} slide is missing required quote ids {sorted(required_ids - observed_ids)}")
        if not observed_ids.issubset(quotes):
            failures.append(f"{role} slide includes unknown quote ids {sorted(observed_ids - quotes)}")

    journey_slide = soup.select_one('[data-slide-role="journey-diagram"]')
    if journey_slide is None:
        failures.append("missing journey-diagram slide")
    else:
        journey = load_journey()
        expected_nodes = {node["id"] for node in journey["nodes"]}  # type: ignore[index]
        observed_nodes = {
            node.get("data-journey-node-id", "").strip()
            for node in journey_slide.select("[data-journey-node-id]")
            if node.get("data-journey-node-id", "").strip()
        }
        if expected_nodes - observed_nodes:
            failures.append("journey diagram is missing one or more required nodes")

    risks_slide = soup.select_one('[data-slide-role="risks-next-steps"]')
    if risks_slide is None:
        failures.append("missing risks-next-steps slide")
    else:
        risks_text = " ".join(risks_slide.stripped_strings).lower()
        if "external agency review" not in risks_text and "separate system" not in risks_text:
            failures.append("risks slide does not acknowledge the external agency boundary")
        if "replacement" not in risks_text and "project management" not in risks_text:
            failures.append("risks slide does not acknowledge the work-management boundary")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)

    print("OK: story fidelity markers align with frozen inputs")


if __name__ == "__main__":
    main()
