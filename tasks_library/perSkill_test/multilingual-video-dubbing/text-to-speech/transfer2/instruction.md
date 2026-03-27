You are given a prompt specification file for announcement generation.

Input files:
- `/root/prompts.json`: list of prompt IDs, text, and target durations.
- `/root/target_language.txt`: language code for speech voice selection.

Produce:
1. `/outputs/prompts/<id>.wav` for every item in `/root/prompts.json`
2. `/outputs/prompt_manifest.json`

Requirements:
- Every prompt WAV must be `48000 Hz`, mono.
- Every prompt must be mastered near `-23 LUFS` (tolerance `±1.5`).
- Absolute duration drift to each `target_duration_sec` must be `<= 0.2 s`.
- Manifest fields per item:
  - `id`, `file`, `target_duration_sec`, `actual_duration_sec`, `drift_sec`, `duration_control`, `lufs`
- `duration_control` must be one of `rate_adjust`, `pad_silence`, `trim`.
