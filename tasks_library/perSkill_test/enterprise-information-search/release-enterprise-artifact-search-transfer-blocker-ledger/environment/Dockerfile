FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.4.1

WORKDIR /root

COPY release_request.json /root/release_request.json
COPY war_room /root/war_room

COPY skills /root/.codex/skills
