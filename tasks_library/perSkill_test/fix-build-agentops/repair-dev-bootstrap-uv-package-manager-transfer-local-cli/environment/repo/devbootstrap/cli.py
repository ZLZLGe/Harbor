from __future__ import annotations

import argparse
import json
from pathlib import Path


def render_report(payload: dict[str, object]) -> str:
    commands = " -> ".join(payload["commands"])
    lines = [
        f"project={payload['project']}",
        f"owner={payload['owner']}",
        f"commands={commands}",
        "status=bootstrap-ready",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="data/bootstrap_seed.json")
    parser.add_argument("--output", default="var/bootstrap_report.txt")
    args = parser.parse_args()

    payload = json.loads(Path(args.seed).read_text(encoding="utf-8"))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(payload), encoding="utf-8")
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
