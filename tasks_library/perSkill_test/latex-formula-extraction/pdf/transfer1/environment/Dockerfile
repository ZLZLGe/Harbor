FROM python:3.12-slim

WORKDIR /root

COPY latex_paper.pdf /root/latex_paper.pdf
COPY expected_transfer1_formula_catalog.json /root/expected_transfer1_formula_catalog.json

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
