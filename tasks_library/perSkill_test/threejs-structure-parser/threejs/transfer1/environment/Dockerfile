FROM python:3.12-slim

ENV NODE_VERSION=20.19.5

WORKDIR /root

RUN mkdir -p /root/data /root/output

RUN python - <<'PY'
import os
import tarfile
import urllib.request

version = os.environ["NODE_VERSION"]
url = f"https://nodejs.org/dist/v{version}/node-v{version}-linux-x64.tar.xz"
archive_path = "/tmp/node.tar.xz"
install_root = "/usr/local/lib/nodejs"
node_root = os.path.join(install_root, f"node-v{version}-linux-x64")

urllib.request.urlretrieve(url, archive_path)
os.makedirs(install_root, exist_ok=True)

with tarfile.open(archive_path, "r:xz") as archive:
    archive.extractall(install_root)

for binary in ("node", "npm", "npx", "corepack"):
    source = os.path.join(node_root, "bin", binary)
    target = os.path.join("/usr/local/bin", binary)
    if os.path.lexists(target):
        os.remove(target)
    os.symlink(source, target)
PY

RUN npm init -y && npm install three@0.170.0

COPY data/robot_scene.js /root/data/robot_scene.js

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
COPY skills /root/.github/skills
