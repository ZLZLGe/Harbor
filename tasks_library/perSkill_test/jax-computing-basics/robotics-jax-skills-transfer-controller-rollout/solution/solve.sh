#!/bin/bash

set -euo pipefail

python3 <<'PY'
import sys

import jax
import jax.numpy as jnp

sys.path.append("/app/skills/jax-skills")
import jax_skills as jx


bundle = jx.load("/app/data/controller_bundle.npz")
params = jx.load("/app/data/dynamics_params.npz")
weights = jx.load("/app/data/cost_weights.npy")

A = jnp.asarray(params["A"])
B = jnp.asarray(params["B"])
K = jnp.asarray(params["K"])
bias = jnp.asarray(params["bias"])
q = weights[:4]
r = weights[4:]


def rollout_one(x0, nominal_controls, disturbances, goal):
    def step(x_t, step_inputs):
        u_nominal, disturbance = step_inputs
        feedback = K @ (goal - x_t)
        u_t = u_nominal + feedback
        x_next = jnp.tanh(A @ x_t + B @ u_t + disturbance + bias) + 0.05 * x_t
        tracking_cost = jnp.sum(q * jnp.square(x_next - goal))
        control_cost = jnp.sum(r * jnp.square(u_t))
        return x_next, (x_next, tracking_cost, control_cost)

    _, (states, tracking_terms, control_terms) = jax.lax.scan(
        step, x0, (nominal_controls, disturbances)
    )
    rollout = jnp.concatenate([x0[None, :], states], axis=0)
    tracking_total = jnp.sum(tracking_terms)
    control_total = jnp.sum(control_terms)
    summary = jnp.stack(
        [tracking_total, control_total, tracking_total + control_total]
    )
    return rollout, summary


@jax.jit
def rollout_batch(initial_states, nominal_controls, disturbances, goal_states):
    return jax.vmap(rollout_one)(
        initial_states, nominal_controls, disturbances, goal_states
    )


robot_rollout, control_cost_summary = rollout_batch(
    bundle["initial_states"],
    bundle["nominal_controls"],
    bundle["disturbances"],
    bundle["goal_states"],
)

jx.save(robot_rollout, "/app/robot_rollout.npy")
jx.save(control_cost_summary, "/app/control_cost_summary.npy")
PY
