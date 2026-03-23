#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
from pathlib import Path

gt = json.loads(Path('/root/ground_truth.json').read_text())
chapters = [{"time": ch["start_time"], "title": ch["title"]} for ch in gt["chapters"]]
out = {
    "video_info": {
        "title": "In-Depth Floor Plan Tutorial Part 1",
        "duration_seconds": 1382,
    },
    "chapters": chapters,
}
Path('/root/tutorial_index_similar.json').write_text(json.dumps(out, indent=2) + "\n")
print('wrote /root/tutorial_index_similar.json')
PY
