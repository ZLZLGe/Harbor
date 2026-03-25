FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.local/share/coursier/bin:${PATH}"

RUN apt-get update && apt-get install -y \
    curl \
    gzip \
    openjdk-17-jdk-headless \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fL https://github.com/coursier/coursier/releases/download/v2.1.25-M23/cs-x86_64-pc-linux.gz \
    | gzip -d > /usr/local/bin/cs \
    && chmod +x /usr/local/bin/cs \
    && cs install scala:2.13.12 scalac:2.13.12

RUN python3 -m pip install --break-system-packages pytest==8.3.5

WORKDIR /root

COPY shift_coverage_planner.py /root/shift_coverage_planner.py
COPY shift_requirements.csv /root/shift_requirements.csv
COPY employee_skills.csv /root/employee_skills.csv
COPY leave_preferences.csv /root/leave_preferences.csv
COPY skills /root/.codex/skills
