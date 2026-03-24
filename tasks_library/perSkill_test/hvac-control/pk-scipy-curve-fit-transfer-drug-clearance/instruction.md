You are preparing a discharge handoff for a patient who received an IV bolus dose. Plasma samples were collected over time, and the team wants a one-compartment decay fit using:

`C(t) = C0 * exp(-k * t)`

Use `/root/iv_bolus_case.json` and write `/root/pk_decay_summary.json` with this structure:

```json
{
  "case_id": "ward-7-discharge-iv-042",
  "drug_name": "gentamicin",
  "input_file": "iv_bolus_case.json",
  "dose_mg": 250.0,
  "samples_used": 10,
  "fit_model": {
    "initial_concentration_mg_per_l": 14.29,
    "elimination_rate_per_hr": 0.173,
    "half_life_hr": 4.01,
    "auc_0_inf_mg_h_per_l": 82.58,
    "rmse_mg_per_l": 0.08
  },
  "discharge_summary": {
    "volume_of_distribution_l": 17.5,
    "clearance_l_per_hr": 3.03,
    "discharge_time_hr": 16.0,
    "subtherapeutic_floor_mg_per_l": 1.2,
    "predicted_concentration_at_discharge_mg_per_l": 0.90,
    "time_to_fall_below_floor_hr": 14.32,
    "dose_due_before_discharge": true
  }
}
```

Requirements:
- Use the plasma sample times and concentrations from the input file for the fit.
- `samples_used` must equal the number of sample rows included in the model fit.
- `half_life_hr` must be derived from the fitted elimination rate.
- `auc_0_inf_mg_h_per_l` must be derived from the fitted model.
- `clearance_l_per_hr` must be consistent with the fitted elimination rate and the provided volume of distribution.
- `predicted_concentration_at_discharge_mg_per_l` and `time_to_fall_below_floor_hr` must come from the fitted decay curve.
- `dose_due_before_discharge` should be `true` when the fitted concentration is predicted to fall below the floor before the stated discharge time.
