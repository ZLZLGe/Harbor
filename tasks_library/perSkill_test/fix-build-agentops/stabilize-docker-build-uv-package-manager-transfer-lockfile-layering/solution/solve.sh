#!/bin/bash
set -euo pipefail

REPO_ROOT=/workspace/incident-digest
cd "$REPO_ROOT"

mkdir -p notes
cat > notes/docker-plan.txt <<'EOF'
The Dockerfile was copying the whole repository before installing dependencies and then exporting a temporary requirements file for pip, which invalidated the dependency cache on every source change. I will switch the image recipe to copy only pyproject.toml, uv.lock, and the vendored wheel first, sync the locked runtime dependencies with uv, then copy the app code and start it with uv run.
EOF

cat > Dockerfile <<'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"
ENV UV_CACHE_DIR="/tmp/uv-cache"
RUN curl -LsSf https://astral.sh/uv/0.9.22/install.sh | sh

COPY pyproject.toml uv.lock ./
COPY vendor ./vendor

RUN uv sync --frozen --no-install-project --no-dev

COPY app ./app

CMD ["uv", "run", "python", "app/main.py"]
EOF

python3 tools/check_recipe.py

if command -v docker >/dev/null 2>&1 && docker version >/dev/null 2>&1; then
  docker build --tag incident-digest-oracle .
  docker run --rm incident-digest-oracle
  docker image rm --force incident-digest-oracle >/dev/null 2>&1 || true
fi
