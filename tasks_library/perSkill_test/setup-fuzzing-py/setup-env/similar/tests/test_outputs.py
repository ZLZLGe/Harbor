from pathlib import Path


base = Path("/root/workspaces")
for repo in ("bytescout", "cfgweave", "pathaudit"):
    assert (base / repo / ".venv" / "bin" / "python").exists(), repo
    assert (base / repo / "status.txt").exists(), repo

summary = Path("/root/similar_env_summary.txt").read_text()
assert "bytescout: requirements workflow complete" in summary
assert "cfgweave: pyproject workflow complete" in summary
assert "pathaudit: requirements workflow complete" in summary
