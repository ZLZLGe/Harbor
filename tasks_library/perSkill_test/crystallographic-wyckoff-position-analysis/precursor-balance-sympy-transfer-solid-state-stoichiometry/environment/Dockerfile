FROM python:3.12-slim

RUN pip3 install --no-cache-dir \
    sympy==1.14.0

RUN mkdir -p /root/workspace /root/reaction_specs

COPY solid_state_reactions.json /root/reaction_specs/

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /etc/claude-code/.claude/skills

WORKDIR /root

CMD ["/bin/bash"]
