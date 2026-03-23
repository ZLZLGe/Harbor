FROM harbor-local-springboot3-java21-verified:latest

WORKDIR /workspace

COPY workspace/ /workspace/
COPY reference/ /root/reference/
COPY skills/ /root/.codex/skills/
COPY skills/ /root/.claude/skills/
COPY skills/ /root/.opencode/skills/
COPY skills/ /root/.goose/skills/
COPY skills/ /root/.factory/skills/
COPY skills/ /root/.agents/skills/
COPY skills/ /root/.gemini/skills/

RUN mkdir -p /logs/verifier

CMD ["/bin/bash"]
