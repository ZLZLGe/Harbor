FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /root

COPY data/ /data/

# codex-hide-skill COPY skills /root/skills
# codex-hide-skill COPY skills /root/.claude/skills
# codex-hide-skill COPY skills /root/.codex/skills
# codex-hide-skill COPY skills /root/.opencode/skill
# codex-hide-skill COPY skills /root/.goose/skills
# codex-hide-skill COPY skills /root/.factory/skills
# codex-hide-skill COPY skills /root/.agents/skills
# codex-hide-skill COPY skills /root/.gemini/skills

RUN mkdir -p /output

CMD ["/bin/bash"]
