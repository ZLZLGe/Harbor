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
  "/root/data/alpha_original.mp4": 18.0,
  "/root/data/alpha_compressed.mp4": 11.0,
  "/root/data/beta_original.mp4": 22.0,
  "/root/data/beta_compressed.mp4": 14.0,
  "/root/data/gamma_original.mp4": 16.0,
  "/root/data/gamma_compressed.mp4": 9.0
}
JSON

RUN printf 'synthetic-media\n' > /root/data/alpha_original.mp4
RUN printf 'synthetic-media\n' > /root/data/alpha_compressed.mp4
RUN printf 'synthetic-media\n' > /root/data/beta_original.mp4
RUN printf 'synthetic-media\n' > /root/data/beta_compressed.mp4
RUN printf 'synthetic-media\n' > /root/data/gamma_original.mp4
RUN printf 'synthetic-media\n' > /root/data/gamma_compressed.mp4

RUN cat > /root/data/alpha_segments.json <<'JSON'
{
  "segments": [
    {"start": 0, "end": 3, "duration": 3, "type": "intro"},
    {"start": 8, "end": 12, "duration": 4, "type": "pause"}
  ]
}
JSON

RUN cat > /root/data/gamma_segments.json <<'JSON'
{
  "segments": [
    {"start": 1, "end": 4, "duration": 3, "type": "dead-air"},
    {"start": 10, "end": 14, "duration": 4, "type": "pause"}
  ]
}
JSON

RUN cat > /root/data/batch_manifest.json <<'JSON'
{
  "batch_id": "promo-slate-2026-q1",
  "jobs": [
    {
      "clip_id": "alpha",
      "original": "/root/data/alpha_original.mp4",
      "compressed": "/root/data/alpha_compressed.mp4",
      "segments": "/root/data/alpha_segments.json"
    },
    {
      "clip_id": "beta",
      "original": "/root/data/beta_original.mp4",
      "compressed": "/root/data/beta_compressed.mp4"
    },
    {
      "clip_id": "gamma",
      "original": "/root/data/gamma_original.mp4",
      "compressed": "/root/data/gamma_compressed.mp4",
      "segments": "/root/data/gamma_segments.json"
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
