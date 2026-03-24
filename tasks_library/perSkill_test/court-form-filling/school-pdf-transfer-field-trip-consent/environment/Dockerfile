FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

RUN pip3 install --break-system-packages \
    pypdf==5.1.0 \
    reportlab==4.2.5

COPY generate_field_trip_form.py /tmp/generate_field_trip_form.py
RUN python3 /tmp/generate_field_trip_form.py /root/field-trip-consent-form.pdf

COPY student-registration.toml /root/student-registration.toml

# Copy skills to agent-specific locations
COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
