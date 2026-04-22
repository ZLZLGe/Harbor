#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path("/root")


def main() -> int:
    fact_sheet = json.loads((ROOT / "fact_sheet.json").read_text(encoding="utf-8"))
    keyword_plan = json.loads((ROOT / "keyword_plan.json").read_text(encoding="utf-8"))
    source_notes = (ROOT / "source_notes.md").read_text(encoding="utf-8")

    print("Confirmed facts:")
    for key, value in fact_sheet.items():
        if key == "unsupported_claims":
            continue
        print(f"- {key}: {value}")

    print("\nForbidden claims:")
    for item in fact_sheet["unsupported_claims"]:
        print(f"- {item}")

    print("\nRoadmap/internal-only notes to avoid in launch copy:")
    for line in source_notes.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and (
            "later release" in stripped
            or "not confirmed" in stripped
            or "long-term roadmap" in stripped
        ):
            print(stripped)

    print("\nKeyword plan:")
    print(f"- primary_keyword: {keyword_plan['primary_keyword']}")
    print(f"- secondary_keywords: {', '.join(keyword_plan['secondary_keywords'])}")
    print(f"- target_slug: {keyword_plan['target_slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
