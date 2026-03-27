FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN pip3 install --break-system-packages \
    numpy==1.26.4 \
    pandas==2.2.2 \
    pyyaml==6.0.1

COPY acc_calibration_runs.csv /root/acc_calibration_runs.csv
COPY benchmark_spec.yaml /root/benchmark_spec.yaml

# codex-hide-skill COPY skills /root/.claude/skills
# codex-hide-skill COPY skills /root/.codex/skills
# codex-hide-skill COPY skills /root/.opencode/skill
# codex-hide-skill COPY skills /root/.goose/skills
# codex-hide-skill COPY skills /root/.factory/skills
# codex-hide-skill COPY skills /root/.agents/skills
# codex-hide-skill COPY skills /root/.gemini/skills
