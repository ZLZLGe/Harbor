Read the YAML files in `/root/configs` and produce `/root/outputs/parsed_values.json`.

Input files (process in this exact order):
1. `configs/region_north.yaml`
2. `configs/region_south.yaml`
3. `configs/region_empty.yaml`
4. `configs/region_legacy.yaml`

Target nested paths (keep this exact order):
1. `telemetry.sampling.hz`
2. `control.pid.lateral.kp`
3. `control.pid.lateral.ki`
4. `safety.fallback.mode`

Output contract:

```json
{
  "target_paths": ["..."],
  "files": [
    {
      "file": "configs/region_north.yaml",
      "load_status": "ok",
      "values": {
        "telemetry.sampling.hz": 20,
        "control.pid.lateral.kp": 0.8,
        "control.pid.lateral.ki": 0.04,
        "safety.fallback.mode": "degraded"
      }
    }
  ],
  "status_counts": {
    "ok": 2,
    "empty": 1,
    "yaml_error": 1
  }
}
```

Rules:
- `load_status` must be one of: `ok`, `empty`, `yaml_error`.
- If a file parses to an empty YAML document (`None`), set `load_status` to `empty`.
- If YAML parsing fails, set `load_status` to `yaml_error`.
- For `empty` and `yaml_error`, set all target-path values to `null`.
- For `ok`, extract each target path from the nested mapping.
- If a target path is missing in an `ok` file, set that path value to `null`.
- Keep file order and target-path order exactly as listed.
- Do not create extra output files.
