#!/usr/bin/env bash
set -euo pipefail

WORKSPACE=/workspace
REPO="$WORKSPACE/repo"
REPORT="$WORKSPACE/reports/release-pipeline-report.md"

cat > "$REPORT" <<'EOF'
# Release pipeline investigation

- 失败的 job 是 `release-image`，下游的 `package-release-bundle` 因为依赖它而被阻塞。
- 失败步骤是 `.github/workflows/release-image.yml` 里的 `docker build -f Dockerfile ...`。
- `release-image.log` 显示 Docker 在执行 `COPY packaging/assets/ /opt/harbor/release/` 时直接报错，提示 `/packaging/assets` 不存在。
- 发布分支已经把发布资源目录改成了 `packaging/release/`，但 `/workspace/repo/Dockerfile` 还保留旧路径，所以镜像构建在复制发布资源时失败。
- 修复方式是把 Dockerfile 中错误的 COPY 源路径改成 `packaging/release/`，这样镜像构建和本地离线 bundle 打包都会读取同一套发布资源。
EOF

python3 - <<'PY'
from pathlib import Path

dockerfile = Path("/workspace/repo/Dockerfile")
text = dockerfile.read_text()
old = "COPY packaging/assets/ /opt/harbor/release/\n"
new = "COPY packaging/release/ /opt/harbor/release/\n"
if old not in text:
    raise SystemExit("expected old COPY instruction not found")
dockerfile.write_text(text.replace(old, new))
PY

bash "$REPO/scripts/run_release_ci.sh"
