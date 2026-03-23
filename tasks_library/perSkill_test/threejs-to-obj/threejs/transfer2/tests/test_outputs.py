import json


def test_link_audit_matches_ground_truth():
    with open("/root/output/link_audit.json", "r", encoding="utf-8") as handle:
        produced = json.load(handle)
    with open("/root/ground_truth/link_audit.json", "r", encoding="utf-8") as handle:
        expected = json.load(handle)
    assert produced == expected
