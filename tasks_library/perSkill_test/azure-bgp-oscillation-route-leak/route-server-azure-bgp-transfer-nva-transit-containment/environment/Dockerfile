FROM python:3.11-slim

# Create directories
RUN mkdir -p /app/data /app/output /app/environment/data

# Copy environment assets used to build the dataset
COPY data /app/environment/data
COPY generate_data.py /app/environment/generate_data.py

# Generate task inputs
RUN python /app/environment/generate_data.py

WORKDIR /app

COPY skills /root/.claude/skills
COPY skills /etc/claude-code/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
