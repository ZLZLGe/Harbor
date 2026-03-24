You are given post-impact accelerometer data from a beam ring-down inspection. Fit the free-decay response with

`a(t) = offset + A * exp(-sigma * t) * sin(2 * pi * f_d * t + phi)`

Where:
- `A` is the initial envelope amplitude in g
- `sigma` is the exponential decay rate in 1/s
- `f_d` is the damped oscillation frequency in Hz
- `phi` is the phase offset in rad
- `offset` is the sensor bias in g

Use `/root/beam_ringdown_case.json` and write `/root/ringdown_modal_fit.json` with this structure:

```json
{
  "inspection_id": "beam-bay-4-ringdown-12",
  "input_file": "beam_ringdown_case.json",
  "beam_serial": "TB-17-042",
  "sensor_axis": "vertical",
  "samples_used": 251,
  "fit_model": {
    "initial_envelope_amplitude_g": 0.82,
    "decay_rate_per_s": 1.35,
    "damped_frequency_hz": 7.40,
    "phase_rad": 0.55,
    "offset_g": -0.004,
    "natural_frequency_hz": 7.40,
    "damping_ratio": 0.029,
    "log_decrement": 0.182,
    "rmse_g": 0.013,
    "r_squared": 0.997
  },
  "inspection_assessment": {
    "minimum_required_damping_ratio": 0.025,
    "threshold_margin": 0.004,
    "evaluation_time_s": 1.5,
    "predicted_envelope_at_evaluation_g": 0.108,
    "amplitude_limit_g": 0.08,
    "time_to_amplitude_limit_s": 1.72,
    "meets_damping_requirement": true,
    "inspection_outcome": "pass"
  }
}
```

Requirements:
- Use all observation rows in the input file for the fit.
- `samples_used` must equal the number of observations included in the model fit.
- `natural_frequency_hz` must be derived from the fitted `decay_rate_per_s` and `damped_frequency_hz`.
- `damping_ratio` must be derived from the fitted `decay_rate_per_s` and `damped_frequency_hz`.
- `log_decrement` should be computed as `2 * pi * damping_ratio / sqrt(1 - damping_ratio^2)`.
- `predicted_envelope_at_evaluation_g` should be `initial_envelope_amplitude_g * exp(-decay_rate_per_s * evaluation_time_s)`.
- `time_to_amplitude_limit_s` should be the first time the fitted envelope reaches `amplitude_limit_g`.
- `threshold_margin` must equal `damping_ratio - minimum_required_damping_ratio`.
- `inspection_outcome` should be `"pass"` when `meets_damping_requirement` is true, otherwise `"fail"`.
