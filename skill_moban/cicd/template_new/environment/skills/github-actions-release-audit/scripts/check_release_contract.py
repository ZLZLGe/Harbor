from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


BROKER = "http://127.0.0.1:8310"
TOKEN = "release-broker-demo-token"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default="/app/workspace")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    bundle_path = Path(args.workspace) / "out" / "release-bundle.json"
    plan_path = Path(args.workspace) / "out" / "promotion-plan.json"
    if not bundle_path.exists() or not plan_path.exists():
        print(
            "contract_hint: bundle or promotion plan is missing; "
            "fix workflow ordering first, especially whether promote waits for attest."
        )
        raise SystemExit(1)

    bundle = load_json(bundle_path)
    plan = load_json(plan_path)
    candidates = requests.get(
        f"{BROKER}/api/v1/release-candidates",
        headers={"X-Release-Broker-Token": TOKEN},
        timeout=10,
    ).json()
    live_plan = requests.get(
        f"{BROKER}/api/v1/promotion-plan",
        headers={"X-Release-Broker-Token": TOKEN},
        params={"release_id": bundle["release_id"]},
        timeout=10,
    ).json()

    print("bundle_source:", bundle["source"])
    print("plan_source:", plan["source"])
    print("bundle_deployable_count:", bundle["summary"]["deployable_count"])
    print("live_candidate_count:", len(candidates["candidates"]))
    print(
        "live_plan_ids:",
        [item["artifact_id"] for item in live_plan["promotions"]],
    )
    print(
        "bundle_deployable_ids:",
        [item["artifact_id"] for item in bundle["artifacts"] if item["deployable"]],
    )
    if plan["source"] == "broker" and bundle["source"] == "broker":
        print("contract_hint: live broker sources are in use")


if __name__ == "__main__":
    main()
