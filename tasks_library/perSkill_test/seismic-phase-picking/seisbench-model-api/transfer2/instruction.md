You have waveform flags at `/root/data/waveform_flags.json`.

Create `/root/transfer2_preprocessing_guardrails.json`.

Requirements:
1. Output valid JSON with top-level keys `record_count` and `records`.
2. `records` must be sorted by `record_id`.
3. Each record must contain exactly these keys: `record_id`, `manual_normalization`, `scale_before_normalization`, `preserve_multiple_arrivals`, `segment_manually`.
4. Use these rules:
   - `manual_normalization = true` for every record
   - `scale_before_normalization = true` only if `amplitude_scale <= 1e-10`; else `false`
   - `preserve_multiple_arrivals = true` for every record
   - `segment_manually = false` for every record
5. Do not read anything from `/tests`.
