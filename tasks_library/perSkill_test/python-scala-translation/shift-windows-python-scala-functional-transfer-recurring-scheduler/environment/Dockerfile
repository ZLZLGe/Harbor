FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    default-jdk \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/share/coursier/bin:$PATH"
RUN curl -fL https://github.com/coursier/coursier/releases/download/v2.1.25-M23/cs-x86_64-pc-linux.gz | gzip -d > cs \
    && chmod +x cs \
    && ./cs setup --yes \
    && ./cs install scala:2.13.12 scalac:2.13.12

WORKDIR /root
COPY ShiftWindowPlanner.py /root/
COPY planner_cases.json /root/

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skills
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
