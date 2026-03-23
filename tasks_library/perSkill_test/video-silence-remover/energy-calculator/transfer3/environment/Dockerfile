FROM python:3.11-slim

WORKDIR /root

RUN pip install --no-cache-dir numpy==1.26.4

RUN mkdir -p /root/data
RUN python3 - <<'PY'
import array
import wave

sample_rate = 8000
line_a = [100, 120, 150, 150, 120, 100]
line_b = [90, 100, 110, 120, 100, 90]

def write_track(path, amplitudes):
    frames = array.array('h')
    for amp in amplitudes:
        frames.extend([amp] * sample_rate)
    with wave.open(path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames.tobytes())

write_track('/root/data/line_a.wav', line_a)
write_track('/root/data/line_b.wav', line_b)
PY

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/skills
COPY skills /root/.gemini/skills
