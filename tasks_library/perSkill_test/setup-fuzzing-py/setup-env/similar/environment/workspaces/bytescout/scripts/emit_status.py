from pathlib import Path

Path("/root/workspaces/bytescout/status.txt").write_text("bytescout-ready\n", encoding="utf-8")
