import json
import os
from pathlib import Path

import pytest


OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
OUTPUT_FILE = OUTPUT_DIR / "branch_prefix_audit.json"


@pytest.fixture(scope="module")
def output_data():
    assert OUTPUT_FILE.exists(), f"Output file {OUTPUT_FILE} does not exist"
    return json.loads(OUTPUT_FILE.read_text())


def audit_by_prefix(output_data):
    return {item["prefix"]: item for item in output_data["prefix_audits"]}


class TestAuditSummary:
    def test_output_structure(self, output_data):
        assert set(output_data.keys()) == {"audit_summary", "prefix_audits"}

    def test_summary_values(self, output_data):
        summary = output_data["audit_summary"]
        assert summary == {
            "audited_prefix_count": 4,
            "violating_prefixes": [
                "172.16.10.0/24",
                "172.16.30.0/24",
                "172.16.40.0/24",
            ],
            "clean_prefixes": ["172.16.20.0/24"],
            "total_leak_paths": 4,
        }

    def test_prefix_order(self, output_data):
        assert [item["prefix"] for item in output_data["prefix_audits"]] == [
            "172.16.10.0/24",
            "172.16.20.0/24",
            "172.16.30.0/24",
            "172.16.40.0/24",
        ]


class TestPrefixAudits:
    EXPECTED = {
        "172.16.10.0/24": {
            "origin_site": "retail-east",
            "origin_asn": 65321,
            "attached_hub_asn": 65302,
            "valley_free_compliant": False,
            "leak_paths": [
                {
                    "path_id": "path-101",
                    "classification": "provider_to_peer",
                    "leaker_asn": 65303,
                    "learned_from_asn": 65301,
                    "exported_to_asn": 65304,
                    "affected_asns": [65301, 65303, 65304, 65321],
                }
            ],
            "acceptable_mitigation_ids": ["mit-02", "mit-05"],
        },
        "172.16.20.0/24": {
            "origin_site": "plant-west",
            "origin_asn": 65322,
            "attached_hub_asn": 65303,
            "valley_free_compliant": True,
            "leak_paths": [],
            "acceptable_mitigation_ids": [],
        },
        "172.16.30.0/24": {
            "origin_site": "finance-north",
            "origin_asn": 65323,
            "attached_hub_asn": 65304,
            "valley_free_compliant": False,
            "leak_paths": [
                {
                    "path_id": "path-301",
                    "classification": "peer_to_provider",
                    "leaker_asn": 65302,
                    "learned_from_asn": 65303,
                    "exported_to_asn": 65301,
                    "affected_asns": [65301, 65302, 65303, 65323],
                },
                {
                    "path_id": "path-302",
                    "classification": "provider_to_peer",
                    "leaker_asn": 65303,
                    "learned_from_asn": 65301,
                    "exported_to_asn": 65302,
                    "affected_asns": [65301, 65302, 65303, 65323],
                },
            ],
            "acceptable_mitigation_ids": ["mit-05", "mit-06"],
        },
        "172.16.40.0/24": {
            "origin_site": "clinic-east",
            "origin_asn": 65324,
            "attached_hub_asn": 65302,
            "valley_free_compliant": False,
            "leak_paths": [
                {
                    "path_id": "path-401",
                    "classification": "provider_to_peer",
                    "leaker_asn": 65304,
                    "learned_from_asn": 65301,
                    "exported_to_asn": 65303,
                    "affected_asns": [65301, 65303, 65304, 65324],
                }
            ],
            "acceptable_mitigation_ids": ["mit-05", "mit-07"],
        },
    }

    @pytest.mark.parametrize("prefix", sorted(EXPECTED))
    def test_prefix_values(self, output_data, prefix):
        audits = audit_by_prefix(output_data)
        assert prefix in audits
        assert audits[prefix] == {"prefix": prefix, **self.EXPECTED[prefix]}

    def test_disruptive_mitigation_not_selected(self, output_data):
        audits = audit_by_prefix(output_data)
        violating_ids = set()
        for prefix in ["172.16.10.0/24", "172.16.30.0/24", "172.16.40.0/24"]:
            violating_ids.update(audits[prefix]["acceptable_mitigation_ids"])
        assert "mit-09" not in violating_ids
