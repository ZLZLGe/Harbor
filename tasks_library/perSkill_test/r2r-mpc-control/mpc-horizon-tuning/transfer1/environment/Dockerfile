FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    pytest==8.4.1

WORKDIR /root

COPY transfer1_thermal_case.json /root/transfer1_thermal_case.json
COPY skills /root/skills
COPY skills /root/.codex/skills

CMD ["/bin/bash"]
