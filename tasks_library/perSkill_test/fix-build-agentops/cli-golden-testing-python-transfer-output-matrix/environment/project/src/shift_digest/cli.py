from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path


REQUIRED_COLUMNS = [
    "ticket_id",
    "owner",
    "team",
    "status",
    "duration_minutes",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a shift digest report.")
    parser.add_argument("--input", required=True, help="Path to the CSV input file.")
    parser.add_argument(
        "--group-by",
        choices=["team", "owner", "status"],
        required=True,
        help="Column used for the report aggregation.",
    )
    parser.add_argument(
        "--min-minutes",
        type=int,
        default=0,
        help="Only keep rows whose duration is at least this value.",
    )
    parser.add_argument(
        "--include-cancelled",
        action="store_true",
        help="Include rows whose status is cancelled.",
    )
    parser.add_argument("--output", required=True, help="Path to the report file.")
    return parser


def load_rows(input_path: Path) -> list[dict[str, str | int]]:
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        rows: list[dict[str, str | int]] = []
        for raw_row in reader:
            rows.append(
                {
                    "ticket_id": raw_row["ticket_id"],
                    "owner": raw_row["owner"],
                    "team": raw_row["team"],
                    "status": raw_row["status"],
                    "duration_minutes": int(raw_row["duration_minutes"]),
                }
            )
    return rows


def filter_rows(
    rows: list[dict[str, str | int]],
    *,
    min_minutes: int,
    include_cancelled: bool,
) -> list[dict[str, str | int]]:
    filtered: list[dict[str, str | int]] = []
    for row in rows:
        if not include_cancelled and row["status"] == "cancelled":
            continue
        if int(row["duration_minutes"]) < min_minutes:
            continue
        filtered.append(row)

    if not filtered:
        raise ValueError("No records matched the provided filters.")

    return filtered


def render_report(rows: list[dict[str, str | int]], group_by: str) -> str:
    buckets: dict[str, dict[str, int]] = defaultdict(
        lambda: {"tickets": 0, "total_minutes": 0}
    )
    for row in rows:
        bucket = buckets[str(row[group_by])]
        bucket["tickets"] += 1
        bucket["total_minutes"] += int(row["duration_minutes"])

    ordered_items = sorted(
        buckets.items(),
        key=lambda item: (-item[1]["total_minutes"], item[0]),
    )

    lines = [
        "Shift Digest",
        f"group_by={group_by}",
        f"rows={len(rows)}",
        f"groups={len(ordered_items)}",
    ]
    for index, (group_name, summary) in enumerate(ordered_items, start=1):
        lines.append(
            f"{index}. {group_name} | tickets={summary['tickets']} | "
            f"total_minutes={summary['total_minutes']}"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        rows = load_rows(Path(args.input))
        filtered_rows = filter_rows(
            rows,
            min_minutes=args.min_minutes,
            include_cancelled=args.include_cancelled,
        )
        report_text = render_report(filtered_rows, args.group_by)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
