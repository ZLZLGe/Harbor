FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir numpy==1.26.4 scipy==1.11.4 scikit-learn==1.4.2 pytest==8.3.2

WORKDIR /root

COPY data /root/data
COPY vendor /root/vendor
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

CMD ["/bin/bash"]
