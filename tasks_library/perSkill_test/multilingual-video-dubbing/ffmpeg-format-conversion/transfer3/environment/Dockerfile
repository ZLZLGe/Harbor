FROM jrottenberg/ffmpeg:6.1-ubuntu

ENTRYPOINT []
WORKDIR /root

COPY input.mp4 /root/input.mp4
COPY skills /root/skills
COPY skills /root/.codex/skills
COPY skills /root/.claude/skills

RUN mkdir -p /logs/verifier /logs/agent /artifacts
