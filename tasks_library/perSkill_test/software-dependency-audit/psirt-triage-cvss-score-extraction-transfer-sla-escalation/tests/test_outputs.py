import json
import os


EXPECTED_OUTPUT = {
    "generated_for_date": "2026-03-20",
    "minimum_cvss_for_escalation": 7.0,
    "escalations": [
        {
            "advisory_id": "NW-PSIRT-2026-041",
            "ticket_id": "OPS-4821",
            "product": "Edge Gateway",
            "owner": "patch-oncall",
            "status": "in_progress",
            "best_vulnerability_id": "CVE-2026-11002",
            "best_cvss_score": 8.7,
            "score_source": "GHSA",
            "sla_due_date": "2026-03-01",
            "days_overdue": 19,
            "published_at": "2026-02-05",
            "bulletin_url": "https://psirt.northwind.example/advisories/NW-PSIRT-2026-041",
        },
        {
            "advisory_id": "NW-PSIRT-2026-058",
            "ticket_id": "OPS-4802",
            "product": "Data Center Orchestrator",
            "owner": "orchestrator-sre",
            "status": "awaiting_patch",
            "best_vulnerability_id": "CVE-2026-15001",
            "best_cvss_score": 9.1,
            "score_source": "RedHat",
            "sla_due_date": "2026-03-05",
            "days_overdue": 15,
            "published_at": "2026-01-29",
            "bulletin_url": "https://psirt.northwind.example/advisories/NW-PSIRT-2026-058",
        },
        {
            "advisory_id": "NW-PSIRT-2026-044",
            "ticket_id": "OPS-4856",
            "product": "Branch Controller",
            "owner": "branch-release",
            "status": "pending_validation",
            "best_vulnerability_id": "CVE-2026-11991",
            "best_cvss_score": 7.4,
            "score_source": "NVD",
            "sla_due_date": "2026-03-15",
            "days_overdue": 5,
            "published_at": "2026-02-18",
            "bulletin_url": "https://psirt.northwind.example/advisories/NW-PSIRT-2026-044",
        },
    ],
}


def get_output_path():
    candidates = [
        os.environ.get("PSIRT_OUTPUT_PATH"),
        "/root/psirt_sla_escalations.json",
        "psirt_sla_escalations.json",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    raise FileNotFoundError("psirt_sla_escalations.json not found")


def main():
    path = get_output_path()
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload == EXPECTED_OUTPUT, "JSON output does not match expected escalation list"


if __name__ == "__main__":
    main()
