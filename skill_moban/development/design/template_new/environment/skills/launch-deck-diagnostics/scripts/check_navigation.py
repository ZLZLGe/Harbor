#!/usr/bin/env python3
from __future__ import annotations

from common import load_html, load_soup


def main() -> None:
    html = load_html()
    soup = load_soup()
    failures: list[str] = []

    if not soup.find(attrs={"data-active-slide-indicator": True}):
        failures.append("missing active slide indicator")
    if not soup.find(attrs={"data-nav-prev": True}):
        failures.append("missing previous navigation control")
    if not soup.find(attrs={"data-nav-next": True}):
        failures.append("missing next navigation control")
    if "ArrowRight" not in html or "ArrowLeft" not in html:
        failures.append("keyboard navigation bindings not found")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)
    print("OK: navigation markers detected")


if __name__ == "__main__":
    main()
