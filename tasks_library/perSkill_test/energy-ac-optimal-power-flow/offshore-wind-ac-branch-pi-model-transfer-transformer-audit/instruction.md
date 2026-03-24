You are supporting the export audit desk for an offshore wind hub. A solved voltage snapshot is already available, but the transformer metering sheet looks inconsistent with the branch parameters. Your job is to recompute the transformer flows and identify which modeling mistake best explains each mismatch.

Use `offshore_transformer_case.json` as the only input. It provides:

- the solved bus voltage magnitudes and angles
- transformer branch parameters with off-nominal tap ratios and phase shifts
- the metering expectations that were handed to the desk

For every transformer, compute the bidirectional AC branch flows under the branch data as modeled, then compare them against the expected metering values. Also evaluate these three alternative mismatch hypotheses for the same transformer:

- `sign_convention_error`: both directional active and reactive injections are reported with the opposite sign
- `tap_ratio_not_applied`: the transformer is recomputed with `tap = 1.0` and the given phase shift
- `phase_shift_sign_error`: the transformer is recomputed with the sign of `shift_deg` reversed and the given tap ratio

Choose `best_matching_model` as the hypothesis with the smallest RMSE across these six fields: `p_from_MW`, `q_from_MVAr`, `s_from_MVA`, `p_to_MW`, `q_to_MVAr`, `s_to_MVA`. Set:

- `status` to `consistent` only when `best_matching_model` is `as_modeled`
- `suspected_issue` to `none`, `sign_convention_error`, `tap_ratio_not_applied`, or `phase_shift_sign_error`
- `delta_expected_minus_actual[field] = expected[field] - actual[field]`
- `max_abs_p_error_MW` as the larger absolute active-power mismatch across the two directions
- `max_abs_q_error_MVAr` as the larger absolute reactive-power mismatch across the two directions
- `max_abs_s_error_MVA` as the larger absolute apparent-power mismatch across the two directions

Write `/root/transformer_diagnostics.json` with the exact structure below. Use MW, MVAr, MVA, per-unit, and degrees as labeled. Round all reported floating-point values to 6 decimal places.

- Sort `diagnostics` by descending `as_modeled_rmse`, then descending `max_abs_s_error_MVA`, then ascending transformer `id`.
- Set `diagnostic_rank` from that sorted order.
- In `summary`, `largest_error_transformer_id` and `largest_as_modeled_rmse` must come from the first item in the sorted `diagnostics` list.

```json
{
  "case_id": "offshore-export-transformer-audit-2042-06-18T04:00:00Z",
  "summary": {
    "transformer_count": 4,
    "consistent_meter_count": 1,
    "suspect_meter_count": 3,
    "largest_as_modeled_rmse": 143.47664,
    "largest_error_transformer_id": "T_WFB",
    "worst_absolute_p_error_MW": 248.969434,
    "worst_absolute_q_error_MVAr": 126.862174,
    "worst_absolute_s_error_MVA": 65.110974
  },
  "diagnostics": [
    {
      "diagnostic_rank": 1,
      "id": "T_WFB",
      "from_bus": 702,
      "to_bus": 710,
      "status": "suspect",
      "suspected_issue": "sign_convention_error",
      "best_matching_model": "sign_convention_error",
      "as_modeled_rmse": 143.47664,
      "max_abs_p_error_MW": 248.969434,
      "max_abs_q_error_MVAr": 18.266732,
      "max_abs_s_error_MVA": 0.0,
      "actual": {
        "p_from_MW": 124.484717,
        "q_from_MVAr": 9.133366,
        "s_from_MVA": 124.819322,
        "p_to_MW": -123.686922,
        "q_to_MVAr": 0.041714,
        "s_to_MVA": 123.686929
      },
      "expected": {
        "p_from_MW": -124.484717,
        "q_from_MVAr": -9.133366,
        "s_from_MVA": 124.819322,
        "p_to_MW": 123.686922,
        "q_to_MVAr": -0.041714,
        "s_to_MVA": 123.686929
      },
      "delta_expected_minus_actual": {
        "p_from_MW": -248.969434,
        "q_from_MVAr": -18.266732,
        "s_from_MVA": 0.0,
        "p_to_MW": 247.373844,
        "q_to_MVAr": -0.083428,
        "s_to_MVA": 0.0
      },
      "candidate_rmse": {
        "as_modeled": 143.47664,
        "sign_convention_error": 0.0,
        "tap_ratio_not_applied": 140.915406,
        "phase_shift_sign_error": 103.157713
      }
    }
  ],
  "issue_counts": {
    "none": 1,
    "sign_convention_error": 1,
    "tap_ratio_not_applied": 1,
    "phase_shift_sign_error": 1
  }
}
```
