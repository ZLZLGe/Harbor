FROM python:3.12.8-slim

RUN pip install --no-cache-dir graphviz==0.20.3
RUN apt-get update && apt-get install -y graphviz && rm -rf /var/lib/apt/lists/*

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

COPY moon_market_script.txt /app/moon_market_script.txt

WORKDIR /app

ENV PYTHONPATH="/root/.codex/skills/dialogue_graph/scripts:/root/.claude/skills/dialogue_graph/scripts:/root/.agents/skills/dialogue_graph/scripts:/root/.opencode/skill/dialogue_graph/scripts"

CMD ["/bin/bash"]
