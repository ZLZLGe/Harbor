You have local phase-picking scenarios at `/root/data/phase_scenarios.json`.

Create `/root/similar_inference_runbook.json`.

Requirements:
1. Output valid JSON with exactly two top-level keys: `scenario_count` and `plans`.
2. `plans` must be sorted by `scenario_id`.
3. Each plan must contain exactly these keys: `scenario_id`, `model_family`, `api_mode`, `pretrained_weights`, `scale_tiny_waveforms`, `treat_as_continuous_stream`.
4. Use these rules:
   - always choose `model_family = "phasenet"`
   - always choose `api_mode = "classify"`
   - always choose `pretrained_weights = "original"`
   - if `amplitude_scale <= 1e-10`, set `scale_tiny_waveforms = true`; otherwise `false`
   - always set `treat_as_continuous_stream = true`
5. Do not read anything from `/tests`.
