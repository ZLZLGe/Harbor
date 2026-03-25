FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY data /root/data
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills

RUN ffmpeg -y \
    -f lavfi -i color=c=maroon:s=160x120:r=25:d=12 \
    -f lavfi -i sine=frequency=523:sample_rate=44100:duration=12 \
    -shortest \
    -c:v libx264 -preset ultrafast -pix_fmt yuv420p \
    -c:a aac -b:a 96k \
    /root/data/input.mp4

CMD ["/bin/bash"]
