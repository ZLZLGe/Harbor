You are given the following files:
- `/root/input.mp4`: base visual timeline with original program audio.
- `/root/segments.srt`: exact window where the narration must be placed.
- `/root/reference_target_text.srt`: target script text.
- `/root/target_language.txt`: language code for speech voice selection.

Produce these outputs:
1. `/outputs/tts_segments/seg_0.wav`
2. `/outputs/dubbed.mp4`
3. `/outputs/report.json`

Requirements:
- Output audio must be `48000 Hz`, mono.
- Apply speech cleanup and mastering before final delivery.
- Integrated loudness target is `-23 LUFS` with tolerance `±1.5`.
- The narration must start at the subtitle window start within `10 ms`.
- End drift relative to the subtitle window end must be `<= 0.2 s`.
- `/outputs/report.json` must include:
  - `source_language`, `target_language`, `audio_sample_rate_hz`, `audio_channels`, `measured_lufs`
  - `speech_segments` list with first object containing:
    - `window_start_sec`, `window_end_sec`, `placed_start_sec`, `placed_end_sec`
    - `window_duration_sec`, `tts_duration_sec`, `drift_sec`, `duration_control`
- `duration_control` must be one of `rate_adjust`, `pad_silence`, `trim`.
