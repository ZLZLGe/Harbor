FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas==2.2.3 \
    PyYAML==6.0.2 \
    pytest==8.4.1

RUN mkdir -p /app/data /app/output

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN mkdir -p /etc/claude-code/.claude/skills
COPY skills/ /etc/claude-code/.claude/skills/

COPY data/ /app/data/

CMD ["/bin/bash"]
