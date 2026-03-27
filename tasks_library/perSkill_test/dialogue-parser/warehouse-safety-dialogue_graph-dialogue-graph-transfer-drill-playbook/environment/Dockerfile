FROM python:3.12.8-slim

RUN pip install --no-cache-dir graphviz==0.20.3

RUN apt-get update && apt-get install -y graphviz && rm -rf /var/lib/apt/lists/*

# codex-hide-skill COPY skills /root/.claude/skills
# codex-hide-skill COPY skills /root/.codex/skills
# codex-hide-skill COPY skills /root/.opencode/skill
# codex-hide-skill COPY skills /root/.goose/skills
# codex-hide-skill COPY skills /root/.factory/skills
# codex-hide-skill COPY skills /root/.agents/skills
# codex-hide-skill COPY skills /root/.gemini/skills

COPY drill_playbook.txt /app/drill_playbook.txt

WORKDIR /app

ENV PYTHONPATH="/root/.codex/skills/dialogue_graph/scripts:/root/.claude/skills/dialogue_graph/scripts:/root/.agents/skills/dialogue_graph/scripts:/root/.opencode/skill/dialogue_graph/scripts"

CMD ["/bin/bash"]
