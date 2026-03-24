You are given a batch bioreactor run with noisy OD600 measurements collected over time.

Use `/root/bioreactor_batch_run.json` to fit the logistic growth model

`OD(t) = K / (1 + exp(-r * (t - t_mid)))`

Where:
- `K` is the carrying capacity in OD600
- `r` is the apparent growth-rate constant in 1/hr
- `t_mid` is the inflection-point time in hr

Then use the fitted model to summarize lag-adjusted growth behavior and the harvest window.

Write `/root/bioreactor_growth_fit.json` with this structure:

```json
{
  "batch_id": "BRX-208A",
  "input_file": "bioreactor_batch_run.json",
  "reactor_volume_l": 1200.0,
  "target_harvest_od600": 1.12,
  "latest_recommended_od600": 1.58,
  "samples_used": 19,
  "fit_model": {
    "initial_od600": 0.013,
    "carrying_capacity_od600": 1.82,
    "growth_rate_per_hr": 0.31,
    "midpoint_time_hr": 16.0,
    "lag_adjusted_onset_hr": 9.55,
    "max_growth_rate_od600_per_hr": 0.141,
    "rmse_od600": 0.011,
    "r_squared": 0.999
  },
  "harvest_forecast": {
    "time_to_target_od600_hr": 17.52,
    "time_to_latest_recommended_od600_hr": 22.08,
    "harvest_window_start_hr": 17.52,
    "harvest_window_end_hr": 22.08,
    "predicted_window_width_hr": 4.56
  }
}
```

Requirements:
- Use all measurement rows in the input file for the fit.
- `samples_used` must equal the number of observations included in the model fit.
- `initial_od600` should be the fitted model prediction at `t = 0`.
- `lag_adjusted_onset_hr` should be computed as `t_mid - 2 / r`.
- `max_growth_rate_od600_per_hr` should be computed from the fitted logistic model.
- The harvest window starts when the fitted curve first reaches `target_harvest_od600` and ends when it first reaches `latest_recommended_od600`.
- `predicted_window_width_hr` should equal the end time minus the start time.
