FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"
RUN curl -LsSf https://astral.sh/uv/0.9.22/install.sh | sh

COPY . .

RUN uv export --no-dev --format requirements-txt -o /tmp/requirements.generated.txt \
    && python -m pip install --no-cache-dir -r /tmp/requirements.generated.txt

CMD ["python", "app/main.py"]
