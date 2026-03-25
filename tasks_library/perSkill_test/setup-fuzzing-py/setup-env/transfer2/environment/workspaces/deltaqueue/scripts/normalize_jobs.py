from pathlib import Path

jobs = []
for raw_line in Path("data/jobs.txt").read_text().splitlines():
    line = raw_line.strip().lower()
    if line:
        jobs.append(line)
Path("/root/transfer2_normalized.txt").write_text("\n".join(jobs) + "\n", encoding="utf-8")
