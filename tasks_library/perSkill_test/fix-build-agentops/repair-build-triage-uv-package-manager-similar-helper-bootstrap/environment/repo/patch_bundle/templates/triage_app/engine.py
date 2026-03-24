from __future__ import annotations

import json
from pathlib import Path

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def build_triage_summary(records: list[dict[str, str]]) -> str:
    ordered = sorted(
        records,
        key=lambda item: (SEVERITY_ORDER[item["severity"]], item["service"]),
    )
    lines = ["Build Triage Summary", f"Total services: {len(records)}", ""]
    for index, item in enumerate(ordered, start=1):
        lines.append(
            f"{index}. {item['service']} [{item['severity']}] -> {item['owner']}"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        raise SystemExit("usage: triage-helper <input_json> <output_txt>")

    input_path = Path(args[0])
    output_path = Path(args[1])
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    summary = build_triage_summary(payload["services"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")
    return 0
