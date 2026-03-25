from pathlib import Path

Path("/root/workspaces/cfgweave/status.txt").write_text("cfgweave-ready\n", encoding="utf-8")
