You are preparing a podcast promo insert.

Input files:
- `/root/bed.wav`: background bed audio.
- `/root/cue.srt`: exact insertion window.
- `/root/promo_text.txt`: narration script.
- `/root/target_language.txt`: language code for speech voice selection.

Produce:
1. `/outputs/tts_segments/seg_0.wav`
2. `/outputs/episode_mix.wav`
3. `/outputs/episode_report.json`

Requirements:
- All outputs must be `48000 Hz`, mono.
- Narration start must match cue window start within `10 ms`.
- Narration end drift to cue window end must be `<= 0.2 s`.
- Integrated loudness target for `/outputs/episode_mix.wav` is `-23 LUFS ±1.5`.
- `/outputs/episode_report.json` must include segment timing fields and `duration_control` from:
  - `rate_adjust`, `pad_silence`, `trim`.
