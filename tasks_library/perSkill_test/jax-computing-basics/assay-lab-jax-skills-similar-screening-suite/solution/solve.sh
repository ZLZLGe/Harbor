#!/bin/bash

set -euo pipefail

python3 <<'PY'
import sys

import jax
import jax.numpy as jnp

sys.path.append("/app/skills/jax-skills")
import jax_skills as jx


plate = jx.load("/app/data/plate_readings.npy")
jx.save(jx.reduce_op(plate, "mean", axis=0), "/app/assay_channel_summary.npy")

residual_bundle = jx.load("/app/data/residual_bundle.npz")
residual = residual_bundle["observed"] - residual_bundle["expected"]
jx.save(jx.map_op(residual, "square"), "/app/residual_energy_map.npy")

binary_panel = jx.load("/app/data/binary_panel.npz")
jx.save(
    jx.logistic_grad(binary_panel["x"], binary_panel["y"], binary_panel["w"]),
    "/app/binder_loss_grad.npy",
)

rollout = jx.load("/app/data/assay_rollout.npz")
jx.save(
    jx.rnn_scan(rollout["seq"], rollout["Wx"], rollout["Wh"], rollout["b"]),
    "/app/assay_state_rollout.npy",
)

network = jx.load("/app/data/network_stack.npz")


def screening_head(x, W1, b1, W2, b2):
    hidden = jax.nn.relu(jnp.dot(x, W1) + b1)
    return jnp.dot(hidden, W2) + b2


logits = jx.jit_run(
    screening_head,
    (network["X"], network["W1"], network["b1"], network["W2"], network["b2"]),
)
jx.save(logits, "/app/screening_head_logits.npy")
PY
