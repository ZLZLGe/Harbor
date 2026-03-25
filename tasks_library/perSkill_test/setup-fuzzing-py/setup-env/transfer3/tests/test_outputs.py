from pathlib import Path


assert Path("/root/workspaces/templategen/.venv/bin/python").exists()
rendered = Path("/root/transfer3_rendered.md").read_text()
assert "# Ops Runbook" in rendered
assert "Owner: platform" in rendered

command_log = Path("/root/transfer3_command_log.md").read_text()
assert "uv sync" in command_log
assert "python -m templategen.cli" in command_log
