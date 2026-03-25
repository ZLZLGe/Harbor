FROM python:3.11-slim

RUN pip install --no-cache-dir numpy==2.2.6 pytest==8.4.1

WORKDIR /root

COPY skills /root/.codex/skills
COPY coating_line_case.json /root/coating_line_case.json
COPY coating_line_simulator.py /root/coating_line_simulator.py
