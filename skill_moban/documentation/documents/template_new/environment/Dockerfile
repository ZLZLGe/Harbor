FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/home/appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    gosu \
    tini \
    unzip \
    zip \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY data/vendor_addendum_redline.docx /app/vendor_addendum_redline.docx
COPY data/review_decisions.json /app/review_decisions.json
COPY skills /app/.codex/skills
COPY skills /home/appuser/.codex/skills
COPY skills /root/.codex/skills
COPY build-scripts/write_protected_hashes.py /opt/documents-task/write_protected_hashes.py

RUN pip install \
    pytest==8.3.3 \
    python-docx==1.1.2

RUN mkdir -p /app/output /logs/verifier /opt/documents-task \
    && python3 /opt/documents-task/write_protected_hashes.py

RUN chown -R appuser:appuser /app /home/appuser /logs/verifier \
    && chmod -R 755 /opt/documents-task

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
