Generate one spoken incident briefing from the updates in `/root/data/incident_updates.json`.

Input:
- `/root/data/incident_updates.json`
- `/root/data/task_config.json`

Save:
- `/root/transfer1_incident_briefing.wav`
- `/root/transfer1_incident_cues.json`

Requirements:
- preserve update order
- include a spoken header with the update code before each update body
- `transfer1_incident_cues.json` must include `segments`, `voice`, `model`, and `total_duration_sec`
- each segment needs `update_code`, `start_sec`, `end_sec`, and `priority`
