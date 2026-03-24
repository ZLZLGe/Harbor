You are assembling an audio envelope analysis bundle in `/app`.

Read these inputs:

- `/app/data/wave_bank.npy`
  - shape `(num_clips, num_samples)`
  - each row is one mono waveform segment
- `/app/data/filterbank_params.npz`
  - `mix`, `b0`, `b1`, `a1`, `env_smooth`, `band_offset`, `drive`
  - each array has shape `(num_bands,)`

For each clip, process samples strictly in time order with a causal filterbank. Initialize every band state to zero:

- `prev_input[k] = 0`
- `prev_output[k] = 0`
- `prev_env[k] = 0`

For each sample `x_t` and each band `k` from `0` to `num_bands - 1`, define:

1. `carry_in` is `x_t` for band `0`, otherwise it is the current output of band `k - 1`.
2. `chain_input_tk = drive[k] * (mix[k] * x_t + (1 - mix[k]) * carry_in)`
3. `y_tk = b0[k] * chain_input_tk + b1[k] * prev_input[k] + a1[k] * prev_output[k] + band_offset[k]`
4. `env_tk = env_smooth[k] * prev_env[k] + (1 - env_smooth[k]) * abs(y_tk)`
5. Update `prev_input[k] = chain_input_tk`, `prev_output[k] = y_tk`, `prev_env[k] = env_tk`

Implement the causal recursion in JAX using `scan`. Batch all clips in one JAX program and JIT-compile the batched evaluator before producing outputs.

Write these files into `/app`:

1. `audio_envelopes.npy`
   - Save the envelope traces as a 2D matrix with shape `(num_clips * num_bands, num_samples)`.
   - Use clip-major row order: all bands of clip `0`, then all bands of clip `1`, and so on.
2. `band_energy_summary.npy`
   - Save a shape `(num_clips, num_bands, 3)` array.
   - The last axis must contain, in this exact order:
     1. mean envelope over time
     2. peak envelope over time
     3. mean squared filtered output over time

The primary output file is `/app/audio_envelopes.npy`.
