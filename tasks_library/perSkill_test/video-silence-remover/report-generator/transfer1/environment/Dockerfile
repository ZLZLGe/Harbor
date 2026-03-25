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

RUN ffmpeg -y -f lavfi -i color=c=maroon:s=160x120:r=25:d=55 -c:v mpeg4 -q:v 5 /root/data/original.mp4 \
    && ffmpeg -y -f lavfi -i color=c=olive:s=160x120:r=25:d=40 -c:v mpeg4 -q:v 5 /root/data/compressed.mp4

CMD ["/bin/bash"]
