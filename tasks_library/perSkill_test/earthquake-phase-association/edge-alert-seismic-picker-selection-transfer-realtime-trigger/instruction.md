You are configuring a first-stage trigger for a remote edge earthquake alert box.

Inputs are in `/root/edge_inputs/`:

- `hardware_profile.json`: the available compute and power budget on the box.
- `realtime_constraints.json`: latency, processing, and false-trigger limits.
- `single_station_summary.csv`: a compact summary of continuous single-station waveform behavior.
- `operator_brief.md`: deployment context and what the operator cares about.

Your task is to choose the most appropriate automatic trigger method family for this deployment and write `/root/edge_trigger_strategy.json`.

Rules:

1. Choose exactly one `method_name` from `sta_lta`, `deep_learning`, or `template_matching`.
2. Base the choice on the hardware limits, the latency budget, the single-station summary, and the operator brief. This is a real-time edge trigger for a low-power box, not an offline high-completeness catalog.
3. Write a JSON object with exactly these top-level keys:
   - `method_name`
   - `key_parameters`
   - `reason`
4. `key_parameters` must be a JSON array of objects. Each object must have exactly these keys:
   - `name`
   - `value`
5. If you choose `sta_lta`, `key_parameters` must contain exactly these five parameter names:
   - `sta_window_seconds`
   - `lta_window_seconds`
   - `trigger_ratio`
   - `detrigger_ratio`
   - `cooldown_seconds`
6. If you choose `sta_lta`, use values in these ranges:
   - `sta_window_seconds`: 0.3 to 1.2
   - `lta_window_seconds`: 4.0 to 12.0
   - `trigger_ratio`: 2.5 to 4.5
   - `detrigger_ratio`: 1.1 to 2.0
   - `cooldown_seconds`: 1.0 to 6.0
7. If you choose `sta_lta`, `lta_window_seconds` must be greater than `4 * sta_window_seconds`, and `trigger_ratio` must be greater than `detrigger_ratio`.
8. `reason` must be a short plain-text explanation in 1 or 2 sentences describing why the selected method fits the hardware, latency, and false-positive tradeoff.

No extra output files are required.
