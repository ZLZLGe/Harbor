import os

import numpy as np


DATA_DIR = "/app/data"
OUTPUT_DIR = "/app"


def expected_outputs():
    bundle = np.load(os.path.join(DATA_DIR, "controller_bundle.npz"))
    params = np.load(os.path.join(DATA_DIR, "dynamics_params.npz"))
    weights = np.load(os.path.join(DATA_DIR, "cost_weights.npy"))

    initial_states = bundle["initial_states"].astype(np.float32)
    nominal_controls = bundle["nominal_controls"].astype(np.float32)
    disturbances = bundle["disturbances"].astype(np.float32)
    goal_states = bundle["goal_states"].astype(np.float32)

    A = params["A"].astype(np.float32)
    B = params["B"].astype(np.float32)
    K = params["K"].astype(np.float32)
    bias = params["bias"].astype(np.float32)
    q = weights[:4].astype(np.float32)
    r = weights[4:].astype(np.float32)

    batch, steps, _ = nominal_controls.shape
    state_dim = initial_states.shape[1]

    rollout = np.zeros((batch, steps + 1, state_dim), dtype=np.float32)
    summary = np.zeros((batch, 3), dtype=np.float32)
    rollout[:, 0, :] = initial_states

    for idx in range(batch):
        x_t = initial_states[idx].copy()
        goal = goal_states[idx]
        tracking_total = np.float32(0.0)
        control_total = np.float32(0.0)

        for step in range(steps):
            u_nominal = nominal_controls[idx, step]
            disturbance = disturbances[idx, step]
            feedback = K @ (goal - x_t)
            u_t = u_nominal + feedback
            x_t = np.tanh(A @ x_t + B @ u_t + disturbance + bias) + np.float32(0.05) * x_t
            rollout[idx, step + 1] = x_t.astype(np.float32)
            tracking_total += np.sum(q * np.square(x_t - goal), dtype=np.float32)
            control_total += np.sum(r * np.square(u_t), dtype=np.float32)

        summary[idx, 0] = tracking_total
        summary[idx, 1] = control_total
        summary[idx, 2] = tracking_total + control_total

    return rollout, summary


def test_output_files_exist():
    assert os.path.exists(os.path.join(OUTPUT_DIR, "robot_rollout.npy"))
    assert os.path.exists(os.path.join(OUTPUT_DIR, "control_cost_summary.npy"))


def test_robot_rollout_matches_expected():
    expected_rollout, _ = expected_outputs()
    actual = np.load(os.path.join(OUTPUT_DIR, "robot_rollout.npy"))
    assert actual.shape == expected_rollout.shape
    assert np.all(np.isfinite(actual))
    assert np.allclose(actual, expected_rollout, rtol=1e-5, atol=1e-6)


def test_cost_summary_matches_expected():
    _, expected_summary = expected_outputs()
    actual = np.load(os.path.join(OUTPUT_DIR, "control_cost_summary.npy"))
    assert actual.shape == expected_summary.shape
    assert np.all(np.isfinite(actual))
    assert np.allclose(actual, expected_summary, rtol=1e-5, atol=1e-6)


def test_rollout_includes_initial_state():
    bundle = np.load(os.path.join(DATA_DIR, "controller_bundle.npz"))
    actual = np.load(os.path.join(OUTPUT_DIR, "robot_rollout.npy"))
    assert np.allclose(actual[:, 0, :], bundle["initial_states"], rtol=1e-6, atol=1e-6)


def test_summary_total_column_is_consistent():
    actual = np.load(os.path.join(OUTPUT_DIR, "control_cost_summary.npy"))
    assert np.allclose(actual[:, 2], actual[:, 0] + actual[:, 1], rtol=1e-6, atol=1e-6)
