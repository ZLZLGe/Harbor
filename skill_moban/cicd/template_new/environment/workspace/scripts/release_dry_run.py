from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from common import WORKSPACE_ROOT, ensure_dirs


WORKFLOW_PATH = WORKSPACE_ROOT / ".github" / "workflows" / "release-dry-run.yml"


def load_jobs() -> dict:
    payload = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    return payload["jobs"]


def execute() -> None:
    ensure_dirs()
    jobs = load_jobs()
    completed: set[str] = set()

    while len(completed) < len(jobs):
        progressed = False
        for job_name, job in jobs.items():
            if job_name in completed:
                continue
            needs = job.get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            if any(name not in completed for name in needs):
                continue
            subprocess.run(job["run"], shell=True, check=True, cwd=WORKSPACE_ROOT)
            completed.add(job_name)
            progressed = True
        if not progressed:
            raise RuntimeError("workflow contains an unsatisfied dependency cycle")


if __name__ == "__main__":
    execute()
