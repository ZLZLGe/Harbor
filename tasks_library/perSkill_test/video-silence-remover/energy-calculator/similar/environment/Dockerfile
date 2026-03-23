FROM python:3.11-slim

WORKDIR /root

RUN pip install --no-cache-dir numpy==1.26.4

RUN mkdir -p /root/data
RUN python3 - <<'PY'
import array
import wave

sample_rate = 8000
amplitudes = [0, 120, 240, 0, 360]
frames = array.array('h')
for amp in amplitudes:
    frames.extend([amp] * sample_rate)

with wave.open('/root/data/lesson_track.wav', 'wb') as wav:
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)
    wav.writeframes(frames.tobytes())
PY

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/skills
COPY skills /root/.gemini/skills
