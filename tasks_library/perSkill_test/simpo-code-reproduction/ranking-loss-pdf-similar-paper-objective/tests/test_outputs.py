import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path("/root/rankbench")
OUTPUT_PATH = Path("/root/ranking_losses.npz")
OBJECTIVE_PATH = ROOT / "rankbench" / "objective.py"
RUNNER_PATH = ROOT / "scripts" / "run_fixed_case.py"
EXPECTED_PATH = Path(__file__).with_name("expected_losses.npz")


def _load_runner_module():
    spec = importlib.util.spec_from_file_location("run_fixed_case_under_test", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _expected_losses() -> np.ndarray:
    return np.load(EXPECTED_PATH)["losses"]


def test_saved_output_matches_expected_vector():
    assert OUTPUT_PATH.exists(), f"Missing output file: {OUTPUT_PATH}"
    result = np.load(OUTPUT_PATH)
    assert "losses" in result.files, f"Missing 'losses' key. Keys: {result.files}"
    np.testing.assert_allclose(result["losses"], _expected_losses(), rtol=1e-7, atol=1e-8)


def test_runner_reproduces_expected_vector(tmp_path):
    sys.path.insert(0, str(ROOT))
    runner = _load_runner_module()
    replay_path = tmp_path / "rerun_losses.npz"
    runner.main(str(replay_path))
    replay = np.load(replay_path)
    np.testing.assert_allclose(replay["losses"], _expected_losses(), rtol=1e-7, atol=1e-8)


def test_runner_calls_completed_function(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT))
    import rankbench.objective as objective_module

    runner = _load_runner_module()

    def sentinel(*args, **kwargs):
        raise RuntimeError("sentinel-function-called")

    monkeypatch.setattr(objective_module, "length_normalized_bt_loss", sentinel)

    with pytest.raises(RuntimeError, match="sentinel-function-called"):
        runner.main(str(tmp_path / "probe_losses.npz"))
