FROM python:3.11-slim

# Create directories
RUN mkdir -p /app/data /app/output /app/environment/data

# Copy environment assets used to build the dataset
COPY data /app/environment/data
COPY generate_data.py /app/environment/generate_data.py

# Generate task inputs
RUN python /app/environment/generate_data.py

WORKDIR /app

# codex-hide-skill COPY skills /root/.claude/skills
# codex-hide-skill COPY skills /etc/claude-code/.claude/skills
# codex-hide-skill COPY skills /root/.codex/skills
# codex-hide-skill COPY skills /root/.opencode/skill
# codex-hide-skill COPY skills /root/.goose/skills
# codex-hide-skill COPY skills /root/.factory/skills
# codex-hide-skill COPY skills /root/.agents/skills
# codex-hide-skill COPY skills /root/.gemini/skills
