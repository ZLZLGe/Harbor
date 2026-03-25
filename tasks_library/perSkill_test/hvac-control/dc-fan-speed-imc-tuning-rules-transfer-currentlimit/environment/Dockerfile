FROM python:3.12-slim

WORKDIR /root

COPY motor_speed_case.toml /root/motor_speed_case.toml
COPY checkpoints_ms.tsv /root/checkpoints_ms.tsv
COPY skills /root/.codex/skills

RUN pip install --no-cache-dir pytest==8.4.1

CMD ["/bin/bash"]
