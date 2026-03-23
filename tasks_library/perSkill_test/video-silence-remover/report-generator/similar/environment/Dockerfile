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
  "/root/data/source_session.mp4": 24.0,
  "/root/data/trimmed_session.mp4": 14.0
}
JSON

RUN printf 'synthetic-media\n' > /root/data/source_session.mp4
RUN printf 'synthetic-media\n' > /root/data/trimmed_session.mp4

RUN cat > /root/data/segments_removed.json <<'JSON'
{
  "segments": [
    {"start": 0, "end": 6, "duration": 6, "type": "intro"},
    {"start": 12, "end": 16, "duration": 4, "type": "pause"}
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
