import json
from pathlib import Path

releases = json.loads(Path("data/releases.json").read_text())
done = [item["name"] for item in releases if item["status"] == "done"]
pending = [item["name"] for item in releases if item["status"] == "pending"]
Path("/root/transfer1_project_report.txt").write_text(
    "completed=" + ",".join(done) + "\n" + "pending=" + ",".join(pending) + "\n",
    encoding="utf-8",
)
