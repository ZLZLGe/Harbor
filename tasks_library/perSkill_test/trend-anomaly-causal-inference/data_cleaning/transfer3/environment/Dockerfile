FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir pandas numpy scikit-learn statsmodels pytest

WORKDIR /root

COPY data /root/data
COPY skills /root/.codex/skills
COPY vendor /root/vendor

CMD ["/bin/bash"]
