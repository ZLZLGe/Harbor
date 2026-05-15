FROM python:3.12-slim

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
        ripgrep \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    astropy==6.1.7 \
    numpy==1.26.4 \
    pandas==2.2.3 \
    pytest==8.4.1

RUN mkdir -p \
      /opt/task-env \
      /root/environment/pipeline \
      /root/workspace \
      /root/answer \
      /root/.agents/skills \
      /root/.codex/skills \
      /tmp/codex-home/skills \
      /logs/agent/skills \
      /logs/verifier

COPY . /opt/task-env
COPY skills /opt/task-env/skills
COPY skills /root/.agents/skills
COPY skills /root/.codex/skills
COPY skills /tmp/codex-home/skills
COPY skills /logs/agent/skills

RUN cp -R /opt/task-env/data/. /root/environment/data/ \
    && cp -R /opt/task-env/workspace/. /root/workspace/ \
    && cp -R /opt/task-env/workspace/. /root/environment/pipeline/ \
    && find /root/environment/data -type f -print0 | sort -z | xargs -0 sha256sum > /opt/task-data.sha256 \
    && chmod 755 /root \
    && chmod -R a+rX /root/environment /root/workspace /root/.agents/skills /root/.codex/skills /tmp/codex-home/skills /logs/agent/skills \
    && chmod 777 /root/answer \
    && chmod +x /root/environment/pipeline/build_followup_packet.py /root/workspace/build_followup_packet.py

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
