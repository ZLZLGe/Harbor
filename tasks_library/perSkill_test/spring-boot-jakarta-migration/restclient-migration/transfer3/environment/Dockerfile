FROM harbor-local-maven-java21:latest

WORKDIR /workspace

COPY workspace/ /workspace/

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skills
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN mkdir -p /logs/verifier

CMD ["/bin/bash"]
