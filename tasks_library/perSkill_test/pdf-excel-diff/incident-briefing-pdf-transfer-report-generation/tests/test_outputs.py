import json
import re
from collections import defaultdict
from pathlib import Path

import pytest
from pypdf import PdfReader

INPUT_JSON = Path("/root/incident_data.json")
OUTPUT_PDF = Path("/root/incident_briefing_report.pdf")
OPEN_STATUSES = {"Active", "Monitoring", "Mitigated"}
SEVERITY_RANK = {"SEV-1": 0, "SEV-2": 1, "SEV-3": 2}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def load_payload():
    return json.loads(INPUT_JSON.read_text())


def load_reader():
    assert OUTPUT_PDF.exists(), f"Missing output PDF: {OUTPUT_PDF}"
    return PdfReader(str(OUTPUT_PDF))


def all_page_text(reader: PdfReader):
    return [normalize(page.extract_text() or "") for page in reader.pages]


def expected_metrics():
    payload = load_payload()
    incidents = payload["incidents"]
    open_incidents = [item for item in incidents if item["status"] in OPEN_STATUSES]
    resolved_incidents = [item for item in incidents if item["status"] == "Resolved"]
    total_customers = sum(item["customers_impacted"] for item in incidents)
    site_totals = defaultdict(int)
    for item in incidents:
        site_totals[item["site"]] += item["customers_impacted"]
    most_impacted_site = max(site_totals.items(), key=lambda pair: (pair[1], pair[0]))[0]
    highest_severity = min(incidents, key=lambda item: SEVERITY_RANK[item["severity"]])["severity"]
    return {
        "briefing": payload["briefing"],
        "actions": payload["leadership_actions"],
        "incidents": incidents,
        "total_incidents": len(incidents),
        "open_incidents": len(open_incidents),
        "resolved_incidents": len(resolved_incidents),
        "highest_severity": highest_severity,
        "total_customers": total_customers,
        "most_impacted_site": most_impacted_site,
        "sorted_ids": [
            item["incident_id"]
            for item in sorted(
                incidents,
                key=lambda item: (SEVERITY_RANK[item["severity"]], item["started_at"]),
            )
        ],
        "highlight_ids": [
            item["incident_id"]
            for item in sorted(
                incidents,
                key=lambda item: (-item["customers_impacted"], SEVERITY_RANK[item["severity"]], item["started_at"]),
            )[:3]
        ],
    }


class TestOutputPdf:
    def test_output_exists(self):
        assert OUTPUT_PDF.exists(), f"Output PDF not found at {OUTPUT_PDF}"

    def test_output_is_readable_and_multipage(self):
        reader = load_reader()
        assert len(reader.pages) >= 3

    def test_metadata_title(self):
        reader = load_reader()
        title = reader.metadata.title if reader.metadata else None
        assert title == "Incident Briefing Report"


class TestOpeningSection:
    @pytest.fixture(scope="class")
    def first_page_text(self):
        reader = load_reader()
        return all_page_text(reader)[0]

    def test_required_headings_present(self, first_page_text):
        assert "Incident Briefing Report" in first_page_text
        assert "Executive Summary" in first_page_text

    def test_briefing_fields_present(self, first_page_text):
        expected = expected_metrics()["briefing"]
        required_lines = [
            f"Briefing Date: {expected['briefing_date']}",
            f"Reporting Window: {expected['reporting_window']}",
            f"Prepared For: {expected['prepared_for']}",
            f"Prepared By: {expected['prepared_by']}",
            f"Command Contact: {expected['command_contact']}",
        ]
        for line in required_lines:
            assert line in first_page_text

    def test_summary_metrics_present(self, first_page_text):
        expected = expected_metrics()
        required_lines = [
            f"Total Incidents: {expected['total_incidents']}",
            f"Open Incidents: {expected['open_incidents']}",
            f"Resolved Incidents: {expected['resolved_incidents']}",
            f"Highest Severity: {expected['highest_severity']}",
            f"Total Customers Impacted: {expected['total_customers']}",
            f"Most Impacted Site: {expected['most_impacted_site']}",
        ]
        for line in required_lines:
            assert line in first_page_text


class TestLeadershipAndHighlights:
    @pytest.fixture(scope="class")
    def full_text(self):
        reader = load_reader()
        return " ".join(all_page_text(reader))

    def test_actions_section_present(self, full_text):
        expected = expected_metrics()
        assert "Leadership Actions" in full_text
        for action in expected["actions"]:
            assert normalize(action) in full_text

    def test_highlights_section_includes_top_incidents(self, full_text):
        expected = expected_metrics()
        assert "Incident Highlights" in full_text
        for incident_id in expected["highlight_ids"]:
            assert incident_id in full_text


class TestDetailedIncidentLog:
    @pytest.fixture(scope="class")
    def full_text(self):
        reader = load_reader()
        return " ".join(all_page_text(reader))

    @pytest.fixture(scope="class")
    def log_text(self, full_text):
        marker = "Detailed Incident Log"
        assert marker in full_text
        return full_text[full_text.index(marker) :]

    def test_log_section_and_headers_present(self, full_text):
        required_headers = [
            "Detailed Incident Log",
            "Incident ID",
            "Title",
            "Site",
            "Severity",
            "Status",
            "Owner",
            "Started",
            "Duration (min)",
            "Impacted Customers",
            "Next Update",
        ]
        for header in required_headers:
            assert header in full_text

    def test_every_incident_is_present(self, full_text):
        expected = expected_metrics()["incidents"]
        for incident in expected:
            assert incident["incident_id"] in full_text
            assert normalize(incident["title"]) in full_text
            assert incident["owner"] in full_text
            assert incident["next_update"] in full_text

    def test_incident_order_matches_requirement(self, log_text):
        ordered_ids = expected_metrics()["sorted_ids"]
        positions = [log_text.index(incident_id) for incident_id in ordered_ids]
        assert positions == sorted(positions)
