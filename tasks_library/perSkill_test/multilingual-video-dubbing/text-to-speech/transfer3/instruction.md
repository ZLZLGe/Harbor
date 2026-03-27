Create an exhibit narration overlay for kiosk playback.

Input files:
- `/root/ambient.wav`: ambient bed audio.
- `/root/window.json`: target start and end time for narration placement.
- `/root/narration.txt`: narration script.
- `/root/target_language.txt`: language code for speech voice selection.

Produce:
1. `/outputs/tts_segments/seg_0.wav`
2. `/outputs/kiosk_mix.wav`
3. `/outputs/kiosk_report.json`

Requirements:
- Output audio must be `48000 Hz`, mono.
- Narration start must match the target window start within `10 ms`.
- End drift must be `<= 0.2 s`.
- Integrated loudness target for `/outputs/kiosk_mix.wav` is `-23 LUFS ±1.5`.
- Report must include placement timing fields and `duration_control` in:
  - `rate_adjust`, `pad_silence`, `trim`.
