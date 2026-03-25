FROM ubuntu:24.04

COPY runtime/python_bundle.tar.gz /tmp/python_bundle.tar.gz
RUN mkdir -p /opt/python \
    && tar -xzf /tmp/python_bundle.tar.gz -C /opt/python \
    && rm /tmp/python_bundle.tar.gz

ENV PATH="/opt/python/bin:${PATH}"
ENV PYTHONHOME="/opt/python"
ENV PYTHONPATH="/opt/python/lib/python3.12/site-packages"
ENV LD_LIBRARY_PATH="/opt/python/lib/x86_64-linux-gnu"

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skills
COPY skills /root/.agents/skills
COPY skills /root/.factory/skills
COPY skills /root/.goose/skills
COPY skills /root/.gemini/skills

COPY clinic_capacity_packet.pdf /root/clinic_capacity_packet.pdf

WORKDIR /root
