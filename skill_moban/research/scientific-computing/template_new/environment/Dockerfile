FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /root/workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        git \
        nodejs \
        npm \
        tini \
        ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    numpy==1.26.4 \
    netCDF4==1.7.2 \
    lxml==5.3.0 \
    pytest==8.4.1

RUN mkdir -p /opt/task-env /root/data /root/workspace /root/output /root/.codex/skills /logs/agent/skills /logs/verifier

COPY . /opt/task-env
COPY skills /opt/task-env/skills
COPY skills /root/.codex/skills
COPY skills /logs/agent/skills

RUN cp -R /opt/task-env/data/. /root/data/ \
    && cp -R /opt/task-env/workspace/. /root/workspace/ \
    && find /root/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-data.sha256 \
    && chmod 755 /root \
    && chmod -R a+rX /root/data /root/workspace /root/.codex/skills /logs/agent/skills \
    && chmod 777 /root/output \
    && chmod +x /root/workspace/run_marine_heat_intake.py

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
