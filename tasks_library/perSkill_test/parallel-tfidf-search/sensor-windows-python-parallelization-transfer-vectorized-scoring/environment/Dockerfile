FROM python:3.11-slim

RUN pip install --no-cache-dir numpy==2.1.3 pytest==8.4.1

WORKDIR /root

COPY workspace/ /root/workspace/
COPY skills /root/.codex/skills
RUN python /root/workspace/build_sensor_assets.py

CMD ["python", "--version"]
