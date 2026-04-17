import csv
import os
from pathlib import Path


OUTPUT_HEADERS = [
    "flow_id",
    "assertion_mode",
    "link_strategy",
    "pom_required",
    "artifact_policy",
    "flake_mitigation",
    "priority",
]


def workspace_root() -> Path:
    return Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))


def parse_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def assertion_mode(row: dict[str, str]) -> str:
    if parse_bool(row["expects_cache_hit"]):
        return "no-requests"
    if parse_bool(row["needs_network_assertion"]):
        return f'includes:{row["response_token"].strip()}'
    return "dom-only"


def link_strategy(row: dict[str, str]) -> str:
    prefetch_visible = parse_bool(row["prefetch_visible"])
    risky_prefetch = (
        parse_bool(row["needs_network_assertion"])
        or parse_bool(row["expects_cache_hit"])
        or parse_bool(row["known_flaky"])
    )
    return "link-accordion-hidden" if prefetch_visible and risky_prefetch else "standard-link"


def pom_required(row: dict[str, str]) -> str:
    criticality = row["criticality"].strip().lower()
    if criticality in {"critical", "high"} or parse_bool(row["uses_wallet"]):
        return "yes"
    return "no"


def artifact_policy(row: dict[str, str]) -> str:
    criticality = row["criticality"].strip().lower()
    if criticality == "critical" or parse_bool(row["known_flaky"]):
        return "trace+video+screenshot"
    return "screenshot-on-failure"


def flake_mitigation(row: dict[str, str]) -> str:
    return "quarantine" if parse_bool(row["known_flaky"]) else "none"


def priority(row: dict[str, str]) -> str:
    criticality = row["criticality"].strip().lower()
    if criticality == "critical" or parse_bool(row["uses_wallet"]):
        return "P0"
    if criticality == "high":
        return "P1"
    if criticality == "medium":
        return "P2"
    return "P3"


def load_rows(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_output_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "flow_id": row["flow_id"].strip(),
        "assertion_mode": assertion_mode(row),
        "link_strategy": link_strategy(row),
        "pom_required": pom_required(row),
        "artifact_policy": artifact_policy(row),
        "flake_mitigation": flake_mitigation(row),
        "priority": priority(row),
    }


def main() -> None:
    root = workspace_root()
    input_path = root / "input" / "browser_flow_cases.csv"
    output_path = root / "output" / "e2e_navigation_plan.csv"

    rows = [build_output_row(row) for row in load_rows(input_path)]
    rows.sort(key=lambda item: item["flow_id"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
