FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

COPY clip_alpha_energies.json /root/
COPY clip_beta_energies.json /root/
COPY clip_gamma_energies.json /root/
COPY batch_config.json /root/

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/skills
COPY skills /root/.gemini/skills
