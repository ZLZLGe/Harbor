import csv
import os
import unittest
from pathlib import Path


EXPECTED_HEADERS = [
    "flow_id",
    "assertion_mode",
    "link_strategy",
    "pom_required",
    "artifact_policy",
    "flake_mitigation",
    "priority",
]

EXPECTED_ROWS = [
    {
        "flow_id": "F-010",
        "assertion_mode": "no-requests",
        "link_strategy": "link-accordion-hidden",
        "pom_required": "yes",
        "artifact_policy": "trace+video+screenshot",
        "flake_mitigation": "quarantine",
        "priority": "P0",
    },
    {
        "flow_id": "F-020",
        "assertion_mode": "includes:catalog-data",
        "link_strategy": "link-accordion-hidden",
        "pom_required": "no",
        "artifact_policy": "screenshot-on-failure",
        "flake_mitigation": "none",
        "priority": "P2",
    },
    {
        "flow_id": "F-030",
        "assertion_mode": "includes:order-summary",
        "link_strategy": "standard-link",
        "pom_required": "yes",
        "artifact_policy": "screenshot-on-failure",
        "flake_mitigation": "none",
        "priority": "P1",
    },
    {
        "flow_id": "F-040",
        "assertion_mode": "dom-only",
        "link_strategy": "standard-link",
        "pom_required": "yes",
        "artifact_policy": "trace+video+screenshot",
        "flake_mitigation": "none",
        "priority": "P0",
    },
    {
        "flow_id": "F-050",
        "assertion_mode": "no-requests",
        "link_strategy": "standard-link",
        "pom_required": "no",
        "artifact_policy": "screenshot-on-failure",
        "flake_mitigation": "none",
        "priority": "P3",
    },
    {
        "flow_id": "F-060",
        "assertion_mode": "includes:balance-update",
        "link_strategy": "link-accordion-hidden",
        "pom_required": "yes",
        "artifact_policy": "trace+video+screenshot",
        "flake_mitigation": "quarantine",
        "priority": "P0",
    },
]


def workspace_root() -> Path:
    return Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))


def output_path() -> Path:
    return workspace_root() / "output" / "e2e_navigation_plan.csv"


def read_rows():
    path = output_path()
    assert path.exists(), f"Missing output CSV: {path}"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        headers = reader.fieldnames
    return headers, rows


class NavigationPlanTests(unittest.TestCase):
    def test_output_matches_expected_plan(self):
        headers, rows = read_rows()
        self.assertEqual(headers, EXPECTED_HEADERS)
        self.assertEqual(rows, EXPECTED_ROWS)

    def test_rows_are_sorted_and_complete(self):
        _, rows = read_rows()
        flow_ids = [row["flow_id"] for row in rows]
        self.assertEqual(flow_ids, sorted(flow_ids))
        for row in rows:
            self.assertEqual(list(row.keys()), EXPECTED_HEADERS)
            for value in row.values():
                self.assertNotIn(value, {"", "null", "NULL", "n/a", "N/A", "None"})

    def test_rule_specific_semantics(self):
        _, rows = read_rows()
        by_id = {row["flow_id"]: row for row in rows}

        self.assertEqual(by_id["F-010"]["assertion_mode"], "no-requests")
        self.assertTrue(by_id["F-020"]["assertion_mode"].startswith("includes:"))
        self.assertEqual(by_id["F-020"]["link_strategy"], "link-accordion-hidden")
        self.assertEqual(by_id["F-040"]["pom_required"], "yes")
        self.assertEqual(by_id["F-060"]["flake_mitigation"], "quarantine")
        self.assertEqual(by_id["F-050"]["artifact_policy"], "screenshot-on-failure")


if __name__ == "__main__":
    unittest.main()
