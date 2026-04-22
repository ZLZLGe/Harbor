from __future__ import annotations

import sys
from pathlib import Path

import yaml


WORKFLOW = Path("/app/workspace/.github/workflows/release-dry-run.yml")


def main() -> None:
    workflow = Path(sys.argv[1]) if len(sys.argv) > 1 else WORKFLOW
    payload = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    print("workflow:", payload.get("name", "unknown"))
    for job_name, job in payload["jobs"].items():
        needs = job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        print(f"- {job_name}: needs={needs}, run={job['run']}")

    promote_needs = payload["jobs"].get("promote", {}).get("needs", [])
    if isinstance(promote_needs, str):
        promote_needs = [promote_needs]
    if promote_needs != ["attest"]:
        print(
            "guardrail_hint: promote should depend only on ['attest']; "
            f"current promote.needs={promote_needs}"
        )


if __name__ == "__main__":
    main()
