FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /root

COPY surge_tank_env.py /root/surge_tank_env.py
COPY tank_controller_scaffold.py /root/tank_controller_scaffold.py
COPY tank_model.yaml /root/tank_model.yaml
COPY tank_cases.csv /root/tank_cases.csv
COPY skills /root/.codex/skills

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    PyYAML==6.0.2 \
    pytest==8.4.1

CMD ["/bin/bash"]
