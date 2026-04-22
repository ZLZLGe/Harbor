from __future__ import annotations

from pathlib import Path

from common import DATA_DIR, OUT_DIR, broker_get, ensure_dirs, read_json, write_json


def render_summary(path: Path, bundle: dict, plan: dict) -> None:
    lines = [
        f"# Release Dry-Run Summary",
        "",
        f"- release_id: {bundle['release_id']}",
        f"- bundle_source: {bundle['source']}",
        f"- promotion_source: {plan['source']}",
        f"- plan_id: {plan.get('plan_id', 'n/a')}",
        f"- deployable_count: {bundle['summary']['deployable_count']}",
        f"- promotion_ready_count: {bundle['summary']['promotion_ready_count']}",
        "",
        "## Promotions",
    ]
    for item in plan.get("promotions", []):
        lines.append(
            f"- {item['artifact_id']} -> {item['target_environment']} ({item['digest']})"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    bundle = read_json(OUT_DIR / "release-bundle.json")

    if bundle["summary"]["promotion_ready_count"] != bundle["summary"]["deployable_count"]:
        plan = read_json(DATA_DIR / "fallback_promotion_plan.json")
    else:
        live_plan = broker_get("/api/v1/promotion-plan", {"release_id": bundle["release_id"]})
        live_ids = {item["artifact_id"] for item in live_plan["promotions"]}
        bundle_ids = {
            item["artifact_id"]
            for item in bundle["artifacts"]
            if item["deployable"]
        }
        if live_ids == bundle_ids:
            plan = live_plan
        else:
            plan = read_json(DATA_DIR / "fallback_promotion_plan.json")

    write_json(OUT_DIR / "promotion-plan.json", plan)
    render_summary(OUT_DIR / "release-summary.md", bundle, plan)


if __name__ == "__main__":
    main()
