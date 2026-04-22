#!/usr/bin/env python3
from __future__ import annotations

from common import REQUIRED_ROLES, collect_slides, load_soup, visible_text


def main() -> None:
    soup = load_soup()
    slides = collect_slides(soup)
    print(f"slides_found={len(slides)}")
    if len(slides) != len(REQUIRED_ROLES):
        print("FAIL: slide count does not match contract")
        raise SystemExit(1)

    failed = False
    for expected_index, (slide, expected_role) in enumerate(zip(slides, REQUIRED_ROLES)):
        role = slide.get("data-slide-role", "").strip()
        if role != expected_role:
            print(f"FAIL: slide {expected_index} role {role!r} != {expected_role!r}")
            failed = True
        if slide.get("data-needs-scroll", "").lower() == "true":
            print(f"FAIL: slide {expected_index} declares scroll-dependent content")
            failed = True
        if not visible_text(slide):
            print(f"FAIL: slide {expected_index} is empty")
            failed = True
    if failed:
        raise SystemExit(1)
    print("OK: no obvious overflow contract failures detected")


if __name__ == "__main__":
    main()
