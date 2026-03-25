You have specialty access cases at `/root/data/specialty_cases.json`.

Create `/root/transfer3_specialty_services.csv`.

Requirements:
1. Sort rows by `request_id`.
2. Write exactly these columns: `request_id`, `scenario_type`, `strategy_code`, `client_target`, `service_family`, `why`.
3. Use these rules:
   - `response_archive` -> `iris_special`, `iris`, `response-format-service`, `special-response-format`
   - `real_time_feed` -> `seedlink`, `seedlink`, `real-time-streaming`, `realtime`
   - `synthetic_waveforms` -> `syngine`, `syngine`, `synthetic-waveforms`, `modelled-synthetics`
   - `earthworm_server` -> `earthworm`, `earthworm`, `custom-wave-server`, `earthworm-source`
   - `neic_edge` -> `neic`, `neic`, `cwb-waveforms`, `neic-edge`
4. Do not read anything from `/tests`.
