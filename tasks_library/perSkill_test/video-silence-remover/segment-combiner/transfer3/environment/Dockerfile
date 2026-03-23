FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

COPY channel_manifest.json /root/
COPY alpha_intro.json /root/
COPY alpha_pause.json /root/
COPY beta_intro.json /root/
COPY beta_pause.json /root/
COPY gamma_intro.json /root/
COPY gamma_pause.json /root/

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/skills
COPY skills /root/.gemini/skills
