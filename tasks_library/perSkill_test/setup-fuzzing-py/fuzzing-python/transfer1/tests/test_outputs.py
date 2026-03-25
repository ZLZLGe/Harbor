import ast
import json
import subprocess
from pathlib import Path

CONFIG = json.loads(Path("/root/data/task_config.json").read_text())
EXPECTED_FUZZ = Path("/root/data/expected_fuzz.py").read_text(encoding="utf-8")


def test_repo_and_outputs_exist():
    repo_root = Path(CONFIG["repo_root"])
    assert repo_root.exists(), f"Missing repo root: {repo_root}"
    assert Path(CONFIG["primary_output_file"]).exists(), "Missing fuzz.py"
    assert Path(CONFIG["fuzz_log_file"]).exists(), "Missing fuzz.log"


def test_fuzz_driver_matches_expected_source():
    driver = Path(CONFIG["primary_output_file"]).read_text(encoding="utf-8")
    assert driver == EXPECTED_FUZZ


def test_fuzz_driver_shape():
    driver_path = Path(CONFIG["primary_output_file"])
    tree = ast.parse(driver_path.read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.Import) and any(alias.name == "atheris" for alias in node.names) for node in tree.body)
    assert any(isinstance(node, ast.FunctionDef) and node.name == "TestOneInput" for node in tree.body)
    source = driver_path.read_text(encoding="utf-8")
    assert "atheris.Setup" in source
    assert "atheris.Fuzz" in source
    assert CONFIG["target_symbol"] in source


def test_fuzz_driver_runs():
    repo_root = Path(CONFIG["repo_root"])
    result = subprocess.run(
        ["python3", "fuzz.py", "-runs=4"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "INITED" in result.stderr
    assert "Done 4 runs in 0 second(s)" in result.stderr


def test_fuzz_log_contains_runtime_markers():
    fuzz_log = Path(CONFIG["fuzz_log_file"]).read_text(encoding="utf-8")
    assert "INITED" in fuzz_log
    assert "Done 6 runs in 0 second(s)" in fuzz_log
