from pathlib import Path


assert Path("/root/workspaces/deltaqueue/.venv/bin/python").exists()
lines = Path("/root/transfer2_normalized.txt").read_text().strip().splitlines()
assert lines == ["job-a", "job-b", "job-c"], lines
