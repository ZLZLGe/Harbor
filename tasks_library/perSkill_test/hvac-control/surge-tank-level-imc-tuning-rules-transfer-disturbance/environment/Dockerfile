FROM python:3.12-slim

WORKDIR /root

COPY surge_tank_case.json /root/surge_tank_case.json
COPY disturbance_schedule.csv /root/disturbance_schedule.csv
COPY surge_tank_simulator.py /root/surge_tank_simulator.py
COPY skills /root/.codex/skills

RUN pip install --no-cache-dir pytest==8.4.1

CMD ["/bin/bash"]
