You are given three damped oscillator scenarios in `relaxation_cases.json`.

For each scenario:

1. Build the initial displaced thermal state from the supplied parameters.
2. Evolve the open oscillator on the provided time grid.
3. Compute the requested relaxation metrics from the photon-number and position-quadrature trajectories.

Do not modify files under `environment/`.

Write `/root/transfer1_relaxation_metrics.csv` with exactly these columns in this order:

`case_id,n_initial,n_final,half_decay_time,integrated_photon_number,final_x_expectation,max_abs_x`

Requirements:

- Keep one row per case.
- Sort rows by `case_id`.
- Round every numeric value to 6 decimal places.
- `half_decay_time` is the earliest grid time at which the photon number is at or below the midpoint between the initial photon number and the thermal equilibrium target.
- `integrated_photon_number` is the trapezoidal time integral of the photon-number trajectory over the full window.
- `final_x_expectation` is the final expectation value of `a + a†`.
- `max_abs_x` is the largest absolute value of the position-quadrature expectation over the full trajectory.

No other output file is required.
