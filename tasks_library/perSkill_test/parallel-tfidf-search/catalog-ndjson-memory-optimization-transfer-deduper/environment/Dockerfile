FROM python:3.11-slim

WORKDIR /root

RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

COPY workspace/ /root/workspace/
COPY skills /root/.codex/skills
COPY skills /root/.claude/skills/
COPY skills /root/.opencode/skill/
COPY skills /root/.goose/skills/
COPY skills /root/.factory/skills/
COPY skills /root/.agents/skills/
COPY skills /root/.gemini/skills/

CMD ["python", "--version"]
