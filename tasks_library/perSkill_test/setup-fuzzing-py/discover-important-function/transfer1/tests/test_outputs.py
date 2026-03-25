from pathlib import Path


report = Path("/root/transfer1_APIs.txt").read_text()
assert "Top files:" in report
assert "Top functions:" in report
assert "mailpiece.parser.parse_message" in report
assert "mailpiece.headers.parse_headers" in report
assert "mailpiece.parts.parse_boundary_section" in report
