#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/app}"

python3 <<'PY'
import os
from pathlib import Path

import numpy as np

try:
    import jax
    import jax.numpy as jnp
except ModuleNotFoundError:
    jax = None
    jnp = None


app_dir = Path(os.environ.get("APP_DIR", "/app"))
data_dir = app_dir / "data"

wave_bank_np = np.load(data_dir / "wave_bank.npy").astype(np.float32)
params_np = np.load(data_dir / "filterbank_params.npz")
num_clips, num_samples = wave_bank_np.shape
num_bands = params_np["mix"].shape[0]

if jax is not None:
    wave_bank = jnp.asarray(wave_bank_np, dtype=jnp.float32)
    params = {name: jnp.asarray(params_np[name], dtype=jnp.float32) for name in params_np.files}

    def process_clip(clip):
        init_state = (
            jnp.zeros((num_bands,), dtype=jnp.float32),
            jnp.zeros((num_bands,), dtype=jnp.float32),
            jnp.zeros((num_bands,), dtype=jnp.float32),
        )

        def sample_step(state, x_t):
            prev_input, prev_output, prev_env = state

            def band_step(carry_in, band_inputs):
                prev_in_k, prev_out_k, prev_env_k, mix, b0, b1, a1, env_smooth, band_offset, drive = band_inputs
                chain_input = drive * (mix * x_t + (1.0 - mix) * carry_in)
                y_t = b0 * chain_input + b1 * prev_in_k + a1 * prev_out_k + band_offset
                env_t = env_smooth * prev_env_k + (1.0 - env_smooth) * jnp.abs(y_t)
                return y_t, (chain_input, y_t, env_t)

            _, (next_input, next_output, next_env) = jax.lax.scan(
                band_step,
                x_t,
                (
                    prev_input,
                    prev_output,
                    prev_env,
                    params["mix"],
                    params["b0"],
                    params["b1"],
                    params["a1"],
                    params["env_smooth"],
                    params["band_offset"],
                    params["drive"],
                ),
            )

            return (next_input, next_output, next_env), (next_output, next_env)

        _, (filtered_seq, env_seq) = jax.lax.scan(sample_step, init_state, clip)
        return filtered_seq.T, env_seq.T

    batched_process = jax.jit(jax.vmap(process_clip, in_axes=0))
    filtered_bank, envelope_bank = batched_process(wave_bank)
    audio_envelopes = envelope_bank.reshape(num_clips * num_bands, num_samples)
    band_energy_summary = jnp.stack(
        [
            jnp.mean(envelope_bank, axis=2),
            jnp.max(envelope_bank, axis=2),
            jnp.mean(jnp.square(filtered_bank), axis=2),
        ],
        axis=-1,
    )
    audio_envelopes = np.asarray(audio_envelopes, dtype=np.float32)
    band_energy_summary = np.asarray(band_energy_summary, dtype=np.float32)
else:
    mix = params_np["mix"].astype(np.float32)
    b0 = params_np["b0"].astype(np.float32)
    b1 = params_np["b1"].astype(np.float32)
    a1 = params_np["a1"].astype(np.float32)
    env_smooth = params_np["env_smooth"].astype(np.float32)
    band_offset = params_np["band_offset"].astype(np.float32)
    drive = params_np["drive"].astype(np.float32)

    filtered_bank = np.zeros((num_clips, num_bands, num_samples), dtype=np.float32)
    envelope_bank = np.zeros((num_clips, num_bands, num_samples), dtype=np.float32)

    for clip_idx in range(num_clips):
        prev_input = np.zeros((num_bands,), dtype=np.float32)
        prev_output = np.zeros((num_bands,), dtype=np.float32)
        prev_env = np.zeros((num_bands,), dtype=np.float32)

        for sample_idx in range(num_samples):
            x_t = wave_bank_np[clip_idx, sample_idx]
            carry_in = np.float32(x_t)
            next_input = np.zeros((num_bands,), dtype=np.float32)
            next_output = np.zeros((num_bands,), dtype=np.float32)
            next_env = np.zeros((num_bands,), dtype=np.float32)

            for band_idx in range(num_bands):
                chain_input = drive[band_idx] * (
                    mix[band_idx] * x_t + (np.float32(1.0) - mix[band_idx]) * carry_in
                )
                y_t = (
                    b0[band_idx] * chain_input
                    + b1[band_idx] * prev_input[band_idx]
                    + a1[band_idx] * prev_output[band_idx]
                    + band_offset[band_idx]
                )
                env_t = env_smooth[band_idx] * prev_env[band_idx] + (
                    np.float32(1.0) - env_smooth[band_idx]
                ) * abs(y_t)

                next_input[band_idx] = chain_input
                next_output[band_idx] = y_t
                next_env[band_idx] = env_t
                carry_in = y_t

            prev_input = next_input
            prev_output = next_output
            prev_env = next_env
            filtered_bank[clip_idx, :, sample_idx] = next_output
            envelope_bank[clip_idx, :, sample_idx] = next_env

    audio_envelopes = envelope_bank.reshape(num_clips * num_bands, num_samples)
    band_energy_summary = np.stack(
        [
            envelope_bank.mean(axis=2),
            envelope_bank.max(axis=2),
            np.square(filtered_bank).mean(axis=2),
        ],
        axis=-1,
    ).astype(np.float32)

np.save(app_dir / "audio_envelopes.npy", audio_envelopes.astype(np.float32))
np.save(app_dir / "band_energy_summary.npy", band_energy_summary.astype(np.float32))
PY
