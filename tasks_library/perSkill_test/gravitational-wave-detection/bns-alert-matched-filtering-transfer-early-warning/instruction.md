You are given a preconditioned long-duration binary-neutron-star alert segment and a small low-mass template bank.

Inputs:

- `/root/data/bns_alert_strain.npz` contains arrays `time_s` and `strain`
- `/root/data/noise_psd.csv` contains columns `frequency_hz,psd`
- `/root/data/bns_template_bank.npz` contains one waveform array per `template_id` plus a shared `relative_time_s` array
- `/root/data/template_bank.json` lists `template_id`, `mass1_solar_mass`, and `mass2_solar_mass`
- `/root/data/alert_context.json` provides `nominal_merger_time_s`

Each template ends at relative time `0` in `relative_time_s`, so the matched-filter peak identifies the detector time of that template endpoint. Use the provided PSD when scoring every template against the strain, choose the single best template overall, and compute:

- `chirp_mass_solar_mass = (mass1_solar_mass * mass2_solar_mass)^(3/5) / (mass1_solar_mass + mass2_solar_mass)^(1/5)`
- `peak_time_s`: detector time at the strongest matched-filter peak for the winning template
- `seconds_before_merger = nominal_merger_time_s - peak_time_s`

Write `/root/bns_early_warning_report.json` with exactly these keys:

```json
{
  "best_template_id": "template id string",
  "mass1_solar_mass": 0.0,
  "mass2_solar_mass": 0.0,
  "chirp_mass_solar_mass": 0.0,
  "peak_snr": 0.0,
  "peak_time_s": 0.0,
  "seconds_before_merger": 0.0
}
```

Use numeric JSON values for all masses and times.
