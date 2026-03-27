from opssuite.policies.yaml_rules import parse_rules_doc


def test_parse_rules_doc():
    doc = parse_rules_doc("owner: ops\nmode: strict")
    assert doc["owner"] == "ops"
