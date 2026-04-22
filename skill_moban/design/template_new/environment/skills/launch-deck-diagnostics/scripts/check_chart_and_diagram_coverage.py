#!/usr/bin/env python3
from __future__ import annotations

from common import load_soup


def main() -> None:
    soup = load_soup()
    failures: list[str] = []

    kpi_slide = soup.select_one('[data-slide-role="kpi-overview"]')
    if kpi_slide is None or not (
        kpi_slide.find("svg")
        or kpi_slide.find("canvas")
        or kpi_slide.select("[data-chart-bar], [data-chart-point], .chart-bar, .chart-point")
    ):
        failures.append("kpi-overview slide is missing a structured chart")

    journey_slide = soup.select_one('[data-slide-role="journey-diagram"]')
    if journey_slide is None or not (
        journey_slide.find("svg")
        or journey_slide.find("canvas")
        or journey_slide.select("[data-journey-node], [data-journey-edge], .journey-node, .journey-edge")
    ):
        failures.append("journey-diagram slide is missing a structured diagram")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)

    print("OK: structured chart and journey coverage detected")


if __name__ == "__main__":
    main()
