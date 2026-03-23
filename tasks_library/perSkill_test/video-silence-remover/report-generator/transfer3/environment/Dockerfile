FROM python:3.11-slim

WORKDIR /root

RUN mkdir -p /root/data /usr/local/bin

RUN cat > /usr/local/bin/ffprobe <<'PY'
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

manifest = Path('/root/data/duration_manifest.json')
if not manifest.exists():
    sys.stderr.write('duration manifest not found\n')
    raise SystemExit(2)

durations = json.loads(manifest.read_text(encoding='utf-8'))
query = Path(sys.argv[-1]).as_posix()

if query in durations:
    print(durations[query])
    raise SystemExit(0)

raw = sys.argv[-1]
if raw in durations:
    print(durations[raw])
    raise SystemExit(0)

sys.stderr.write(f'unknown media path: {raw}\n')
raise SystemExit(1)
PY
RUN chmod +x /usr/local/bin/ffprobe

RUN cat > /root/data/duration_manifest.json <<'JSON'
{
  "/root/data/master_source.mp4": 24.0,
  "/root/data/candidate_a.mp4": 18.0,
  "/root/data/candidate_b.mp4": 13.0,
  "/root/data/candidate_c.mp4": 10.0
}
JSON

RUN printf 'synthetic-media\n' > /root/data/master_source.mp4
RUN printf 'synthetic-media\n' > /root/data/candidate_a.mp4
RUN printf 'synthetic-media\n' > /root/data/candidate_b.mp4
RUN printf 'synthetic-media\n' > /root/data/candidate_c.mp4

RUN cat > /root/data/candidate_a_segments.json <<'JSON'
{
  "segments": [
    {"start": 0, "end": 4, "duration": 4, "type": "intro"},
    {"start": 14, "end": 16, "duration": 2, "type": "pause"}
  ]
}
JSON

RUN cat > /root/data/candidate_b_segments.json <<'JSON'
{
  "segments": [
    {"start": 0, "end": 5, "duration": 5, "type": "intro"},
    {"start": 11, "end": 17, "duration": 6, "type": "pause"}
  ]
}
JSON

RUN cat > /root/data/candidate_c_segments.json <<'JSON'
{
  "segments": [
    {"start": 0, "end": 6, "duration": 6, "type": "intro"},
    {"start": 8, "end": 16, "duration": 8, "type": "pause"}
  ]
}
JSON

RUN cat > /root/data/candidate_manifest.json <<'JSON'
{
  "target_window": {
    "min_pct": 30,
    "max_pct": 55,
    "target_pct": 42
  },
  "candidates": [
    {
      "candidate_id": "candidate_a",
      "compressed": "/root/data/candidate_a.mp4",
      "segments": "/root/data/candidate_a_segments.json"
    },
    {
      "candidate_id": "candidate_b",
      "compressed": "/root/data/candidate_b.mp4",
      "segments": "/root/data/candidate_b_segments.json"
    },
    {
      "candidate_id": "candidate_c",
      "compressed": "/root/data/candidate_c.mp4",
      "segments": "/root/data/candidate_c_segments.json"
    }
  ]
}
JSON

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/skills
COPY skills /root/.gemini/skills
