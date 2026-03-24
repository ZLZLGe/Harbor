import json
from pathlib import Path

import numpy as np
import torch


EXPECTED_FIELDS = {
    "dataset",
    "seed",
    "total_steps",
    "checkpoint_step",
    "batch_size",
    "block_size",
    "continuous_loss_trace",
    "resumed_loss_trace",
    "continuous_final_val_loss",
    "resumed_final_val_loss",
    "max_train_loss_delta",
    "final_val_loss_delta",
    "max_parameter_delta",
    "max_exp_avg_delta",
    "max_exp_avg_sq_delta",
    "continuous_final_lr",
    "resumed_final_lr",
    "continuous_tokens_seen",
    "resumed_tokens_seen",
    "scaler_enabled",
    "scaler_scale_delta",
    "checkpoint_path",
}


def path_exists(path):
    try:
        return path.exists()
    except PermissionError:
        return False


def find_output_file():
    candidates = [
        Path("resume_consistency_report.json"),
        Path("/root/resume_consistency_report.json"),
        Path(__file__).resolve().parent.parent / "resume_consistency_report.json",
        Path.cwd() / "resume_consistency_report.json",
    ]
    for path in candidates:
        if path_exists(path):
            return path

    matches = list(Path(".").rglob("resume_consistency_report.json"))
    if matches:
        return matches[0]
    return Path("/root/resume_consistency_report.json")


OUTPUT_FILE = find_output_file()


def load_results():
    assert OUTPUT_FILE.exists(), f"resume_consistency_report.json not found at {OUTPUT_FILE}"
    with OUTPUT_FILE.open() as f:
        return json.load(f)


def load_checkpoint():
    results = load_results()
    checkpoint_path = Path(results["checkpoint_path"])
    assert checkpoint_path.exists(), f"checkpoint not found at {checkpoint_path}"
    return torch.load(checkpoint_path, map_location="cpu")


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), f"resume_consistency_report.json not found at {OUTPUT_FILE}"


def test_top_level_schema_matches_instruction():
    results = load_results()
    assert set(results.keys()) == EXPECTED_FIELDS


def test_identity_fields_match_dataset_manifest():
    results = load_results()
    assert results["dataset"] == "resume_parity_tokens"
    assert results["seed"] == 2026
    assert results["total_steps"] == 12
    assert results["checkpoint_step"] == 6
    assert results["batch_size"] == 4
    assert results["block_size"] == 32


def test_loss_traces_have_expected_length_and_range():
    results = load_results()
    for key in ["continuous_loss_trace", "resumed_loss_trace"]:
        trace = results[key]
        assert isinstance(trace, list)
        assert len(trace) == results["total_steps"]
        values = np.asarray(trace, dtype=float)
        assert np.all(np.isfinite(values))
        assert np.all(values > 0.0)
        assert np.all(values < 10.0)


def test_reported_deltas_match_trace_math():
    results = load_results()
    continuous = np.asarray(results["continuous_loss_trace"], dtype=float)
    resumed = np.asarray(results["resumed_loss_trace"], dtype=float)
    expected_max = float(np.max(np.abs(continuous - resumed)))
    assert abs(results["max_train_loss_delta"] - expected_max) < 1e-12

    expected_val_delta = abs(results["continuous_final_val_loss"] - results["resumed_final_val_loss"])
    assert abs(results["final_val_loss_delta"] - expected_val_delta) < 1e-12


def test_resume_parity_is_tight():
    results = load_results()
    assert results["max_train_loss_delta"] < 1e-4
    assert results["final_val_loss_delta"] < 1e-4
    assert results["max_parameter_delta"] < 1e-4
    assert results["max_exp_avg_delta"] < 1e-4
    assert results["max_exp_avg_sq_delta"] < 1e-4
    assert abs(results["continuous_final_lr"] - results["resumed_final_lr"]) < 1e-12


def test_token_accounting_matches_schedule():
    results = load_results()
    expected_tokens = results["total_steps"] * results["batch_size"] * results["block_size"]
    assert results["continuous_tokens_seen"] == expected_tokens
    assert results["resumed_tokens_seen"] == expected_tokens


def test_scaler_field_is_consistent():
    results = load_results()
    assert isinstance(results["scaler_enabled"], bool)
    assert np.isfinite(results["scaler_scale_delta"])
    assert results["scaler_scale_delta"] >= 0.0
    if not results["scaler_enabled"]:
        assert results["scaler_scale_delta"] == 0.0


def test_checkpoint_exists_and_has_required_state():
    results = load_results()
    checkpoint = load_checkpoint()
    assert Path(results["checkpoint_path"]).name == "resume_step_6.pt"
    required_keys = {
        "step",
        "model",
        "optimizer",
        "scaler",
        "torch_rng_state",
        "numpy_rng_state",
        "python_rng_state",
        "train_data_state",
    }
    assert required_keys.issubset(checkpoint.keys())
    assert checkpoint["step"] == results["checkpoint_step"]


def test_checkpoint_contains_replayable_data_state():
    checkpoint = load_checkpoint()
    train_state = checkpoint["train_data_state"]
    assert "generator_state" in train_state
    assert "batches_emitted" in train_state
    assert int(train_state["batches_emitted"]) == checkpoint["step"]


def test_final_losses_are_finite_and_close():
    results = load_results()
    for key in ["continuous_final_val_loss", "resumed_final_val_loss"]:
        value = results[key]
        assert isinstance(value, (int, float))
        assert np.isfinite(value)
        assert 0.0 < value < 10.0
    assert abs(results["continuous_final_val_loss"] - results["resumed_final_val_loss"]) < 1e-4
