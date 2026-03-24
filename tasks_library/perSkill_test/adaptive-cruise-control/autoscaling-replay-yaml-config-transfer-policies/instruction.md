Implement a request-replay autoscaling simulator for a single cloud service. The simulator must load the full autoscaling configuration from the provided structured rules file, replay the provided workload CSV in time order, and write a primary policy artifact that summarizes both the rules in effect and the achieved performance.

Create these files:

`policy_engine.py`
- Define class `AutoscalingPolicyEngine`.
- Constructor: `__init__(self, config)` where `config` is the nested dict loaded from the provided rules file under the top-level `autoscaling` key.
- Methods:
  - `reset()`
  - `project_latency(request_rps, cpu_utilization_pct, instance_count)` returning a float
  - `evaluate(minute, request_rps, cpu_utilization_pct)` returning a dict with keys:
    - `action`
    - `instance_count`
    - `request_ratio`
    - `projected_latency_ms`
    - `slo_met`
    - `cooldown_blocked`
- `reset()` must restore `instance_count` to `service.initial_instances` and clear the last scale-up and scale-down timestamps.
- `project_latency(...)` must use this formula with the service coefficients from the rules file:

```text
request_ratio = request_rps / (instance_count * capacity_rps_per_instance)
overload = max(0.0, request_ratio - 0.7)
cpu_over = max(0.0, cpu_utilization_pct - 60.0)
projected_latency_ms =
    base_latency_ms
    + overload * latency_penalty_ms_per_over_capacity
    + cpu_over * cpu_penalty_ms_per_pct_over_60
```

- `evaluate(...)` must follow this decision order exactly:
  - Start from the current `instance_count`.
  - Compute the pre-decision `request_ratio` and `projected_latency_ms` using the current instance count.
  - `scale_up_signal` is true when any scale-up threshold is met or exceeded.
  - `scale_down_signal` is true when all scale-down thresholds are met.
  - If `scale_up_signal` is true, handle scale-up first. Only consider scale-down when `scale_up_signal` is false.
  - A direction is cooldown-ready when either no prior action of that direction has happened, or `(minute - last_direction_minute) / dt_minutes >= cooldown_steps[direction]`.
  - When a signal is present but its direction is still cooling down, return `cooldown_blocked = True` and keep the current instance count.
  - When scale-up is allowed, move to `min(max_instances, current_instances + scale_up.step)` and set `action` to `scale_up_<delta>`.
  - When scale-down is allowed, move to `max(min_instances, current_instances - scale_down.step)` and set `action` to `scale_down_<delta>`.
  - Otherwise use `action = hold`.
  - After the action decision, recompute `request_ratio` and `projected_latency_ms` using the resulting `instance_count`.
  - `slo_met` is true when the post-decision projected latency is at or below `slo.latency_p95_ms`.

`autoscaling_replay.py`
- Load the provided rules file and `workload_metrics.csv` at runtime.
- Do not hard-code service limits, cooldowns, thresholds, model coefficients, or latency SLO values.
- Replay every row in `workload_metrics.csv` in timestamp order.
- Write these outputs:
  - the primary policy artifact
  - `autoscaling_results.csv`
  - `autoscaling_report.md`

Input files:
- the provided structured rules file
- `workload_metrics.csv`

The rules file contains nested sections for:
- replay timing and cooldown steps
- service limits and latency model coefficients
- scale-up and scale-down thresholds
- latency SLO targets

`workload_metrics.csv` columns:
- `minute`
- `request_rps`
- `cpu_utilization_pct`

Replay requirements:
- Duration: 75 minutes
- Time step: 5 minutes
- Keep instance count within the configured min/max bounds at all times
- Honor separate cooldown windows for scale-up and scale-down decisions
- Produce at least 2 scale-up events and at least 2 scale-down events during the replay
- Achieve latency compliance ratio at least the configured target ratio

The primary policy artifact must use this nested structure:

```
replay:
  rows_processed: <int>
  dt_minutes: <int>
service:
  name: <string>
  min_instances: <int>
  max_instances: <int>
  initial_instances: <int>
  final_instances: <int>
policy:
  cooldown_steps:
    scale_up: <int>
    scale_down: <int>
  scale_up:
    request_ratio_threshold: <float>
    cpu_threshold_pct: <float>
    latency_threshold_ms: <float>
    step: <int>
  scale_down:
    request_ratio_threshold: <float>
    cpu_threshold_pct: <float>
    latency_threshold_ms: <float>
    step: <int>
results:
  actions_taken:
    scale_up: <int>
    scale_down: <int>
    hold: <int>
  achieved:
    latency_slo_ms: <float>
    compliance_ratio: <float>
    max_projected_latency_ms: <float>
    average_instances: <float>
    estimated_cost_usd: <float>
    cooldown_blocks: <int>
    peak_request_ratio: <float>
  timeline:
    first_scale_up_minute: <int>
    first_scale_down_minute: <int>
overall:
  target_compliance_ratio_met: <bool>
  constraints_respected: <bool>
```

`autoscaling_results.csv` requirements:
- Exactly the same number of rows as `workload_metrics.csv`
- Exact column order:

```csv
minute,request_rps,cpu_utilization_pct,instance_count,action,request_ratio,projected_latency_ms,slo_met,cooldown_blocked
```

Summary-field definitions:
- `rows_processed`: number of replayed workload rows
- `final_instances`: the post-decision instance count from the last replay row
- `actions_taken`: counts of rows whose action bucket is scale-up, scale-down, or hold
- `compliance_ratio`: fraction of replay rows with `slo_met = true`
- `max_projected_latency_ms`: maximum post-decision projected latency across replay rows
- `average_instances`: arithmetic mean of the post-decision `instance_count` values
- `estimated_cost_usd`: `average_instances * instance_hour_cost_usd * (rows_processed * dt_minutes / 60.0)`
- `cooldown_blocks`: number of replay rows where `cooldown_blocked = true`
- `peak_request_ratio`: maximum post-decision `request_ratio` across replay rows
- `first_scale_up_minute` and `first_scale_down_minute`: the first replay minute whose action bucket is scale-up or scale-down
- `target_compliance_ratio_met`: whether `compliance_ratio >= slo.compliance_target_ratio`
- `constraints_respected`: whether every replay row keeps `instance_count` within the configured min/max bounds

`autoscaling_report.md` must include short sections covering:
- system design
- scaling decisions
- replay results

Do not modify the provided input files.
