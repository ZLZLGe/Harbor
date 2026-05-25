FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN for attempt in 1 2 3; do \
      apt-get update -o Acquire::Retries=3 && \
      apt-get install -y --no-install-recommends python3 ca-certificates && \
      rm -rf /var/lib/apt/lists/* && \
      exit 0; \
      echo "apt attempt ${attempt} failed, retrying" >&2; \
      sleep 5; \
    done; \
    exit 1

WORKDIR /root

COPY scan_data.stl /root/

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
