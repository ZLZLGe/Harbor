FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg

WORKDIR /root

COPY archive-source.mp4 /tmp/archive-source.mp4

RUN ffmpeg -y -i /tmp/archive-source.mp4 \
    -vf "scale=960:540,format=gray,eq=contrast=1.10:brightness=-0.06,drawbox=x=0:y=0:w=iw:h=42:color=black@0.75:t=fill,drawbox=x=0:y=ih-30:w=iw:h=30:color=black@0.65:t=fill" \
    -an \
    -c:v libx264 \
    -preset veryfast \
    -crf 23 \
    -g 30 \
    -pix_fmt yuv420p \
    /root/archive-camera.mp4

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
