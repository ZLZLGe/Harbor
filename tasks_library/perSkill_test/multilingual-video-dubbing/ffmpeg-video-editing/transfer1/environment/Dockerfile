FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
    pytest==8.3.4 \
    imageio-ffmpeg==0.6.0

RUN python - <<'PY'
import os
import imageio_ffmpeg

src = imageio_ffmpeg.get_ffmpeg_exe()
dst = "/usr/local/bin/ffmpeg"
if os.path.lexists(dst):
    os.remove(dst)
os.symlink(src, dst)
print(f"ffmpeg linked: {src} -> {dst}")
PY

WORKDIR /root

COPY input.mp4 /root/input.mp4

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

CMD ["/bin/bash"]
