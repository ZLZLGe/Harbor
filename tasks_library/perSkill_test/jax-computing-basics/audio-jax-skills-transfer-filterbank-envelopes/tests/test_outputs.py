import os

import numpy as np


APP_DIR = os.environ.get("APP_DIR", "/app")
DATA_DIR = os.path.join(APP_DIR, "data")
OUTPUT_DIR = APP_DIR


def expected_outputs():
    wave_bank = np.load(os.path.join(DATA_DIR, "wave_bank.npy")).astype(np.float32)
    params = np.load(os.path.join(DATA_DIR, "filterbank_params.npz"))

    mix = params["mix"].astype(np.float32)
    b0 = params["b0"].astype(np.float32)
    b1 = params["b1"].astype(np.float32)
    a1 = params["a1"].astype(np.float32)
    env_smooth = params["env_smooth"].astype(np.float32)
    band_offset = params["band_offset"].astype(np.float32)
    drive = params["drive"].astype(np.float32)

    num_clips, num_samples = wave_bank.shape
    num_bands = mix.shape[0]

    filtered_bank = np.zeros((num_clips, num_bands, num_samples), dtype=np.float32)
    envelope_bank = np.zeros((num_clips, num_bands, num_samples), dtype=np.float32)

    for clip_idx in range(num_clips):
        prev_input = np.zeros((num_bands,), dtype=np.float32)
        prev_output = np.zeros((num_bands,), dtype=np.float32)
        prev_env = np.zeros((num_bands,), dtype=np.float32)

        for sample_idx in range(num_samples):
            x_t = wave_bank[clip_idx, sample_idx]
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
                ) * np.abs(y_t)

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
            np.mean(envelope_bank, axis=2),
            np.max(envelope_bank, axis=2),
            np.mean(np.square(filtered_bank), axis=2),
        ],
        axis=-1,
    )
    return audio_envelopes, band_energy_summary


def test_output_files_exist():
    assert os.path.exists(os.path.join(OUTPUT_DIR, "audio_envelopes.npy"))
    assert os.path.exists(os.path.join(OUTPUT_DIR, "band_energy_summary.npy"))


def test_audio_envelopes_match_expected():
    expected_audio, _ = expected_outputs()
    actual = np.load(os.path.join(OUTPUT_DIR, "audio_envelopes.npy"))
    assert actual.shape == expected_audio.shape
    assert np.all(np.isfinite(actual))
    assert np.all(actual >= 0.0)
    assert np.allclose(actual, expected_audio, rtol=1e-5, atol=1e-6)


def test_band_energy_summary_matches_expected():
    _, expected_summary = expected_outputs()
    actual = np.load(os.path.join(OUTPUT_DIR, "band_energy_summary.npy"))
    assert actual.shape == expected_summary.shape
    assert np.all(np.isfinite(actual))
    assert np.allclose(actual, expected_summary, rtol=1e-5, atol=1e-6)


def test_summary_consistent_with_primary_output():
    wave_bank = np.load(os.path.join(DATA_DIR, "wave_bank.npy"))
    params = np.load(os.path.join(DATA_DIR, "filterbank_params.npz"))
    num_clips = wave_bank.shape[0]
    num_bands = params["mix"].shape[0]

    envelopes = np.load(os.path.join(OUTPUT_DIR, "audio_envelopes.npy")).reshape(
        num_clips, num_bands, wave_bank.shape[1]
    )
    summary = np.load(os.path.join(OUTPUT_DIR, "band_energy_summary.npy"))

    assert np.allclose(summary[:, :, 0], envelopes.mean(axis=2), rtol=1e-6, atol=1e-6)
    assert np.allclose(summary[:, :, 1], envelopes.max(axis=2), rtol=1e-6, atol=1e-6)


def test_clip_major_row_order():
    expected_audio, _ = expected_outputs()
    actual = np.load(os.path.join(OUTPUT_DIR, "audio_envelopes.npy"))
    assert np.allclose(actual[0], expected_audio[0], rtol=1e-6, atol=1e-6)
    assert np.allclose(actual[-1], expected_audio[-1], rtol=1e-6, atol=1e-6)
