from pathlib import Path


assert Path("/root/workspaces/releaseledger/.venv/bin/python").exists()
report = Path("/root/transfer1_project_report.txt").read_text()
assert "completed=alpha" in report
assert "pending=beta" in report
