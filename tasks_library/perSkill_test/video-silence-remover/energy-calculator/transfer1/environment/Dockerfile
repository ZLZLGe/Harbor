FROM python:3.11-slim

WORKDIR /root

RUN pip install --no-cache-dir numpy==1.26.4

RUN mkdir -p /root/data
RUN python3 - <<'PY'
import array
import wave

sample_rate = 8000
window_samples = int(sample_rate * 0.5)
amplitudes = [20, 60, 140, 300, 300, 140, 60, 20]
frames = array.array('h')
for amp in amplitudes:
    frames.extend([amp] * window_samples)

with wave.open('/root/data/broadcast_clip.wav', 'wb') as wav:
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
