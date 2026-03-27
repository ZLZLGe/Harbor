FROM python:3.12-slim

WORKDIR /root

COPY latex_paper.pdf /root/latex_paper.pdf
COPY expected_transfer2_formula_metrics.csv /root/expected_transfer2_formula_metrics.csv

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
