from pathlib import Path


report = Path("/root/transfer2_oracle_map.md").read_text()
assert "parse_rule_block" in report
assert "duplicate environment keys" in report
assert "parse_schedule" in report
assert "invalid minute values" in report
assert "load_policy_document" in report
assert "preserved" in report
