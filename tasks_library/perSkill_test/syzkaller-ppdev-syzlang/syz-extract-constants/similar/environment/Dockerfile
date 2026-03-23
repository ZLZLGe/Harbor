FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.3.4 pytest-json-ctrf==0.3.6
RUN printf '%s\n' \
    '#!/bin/sh' \
    'set -eu' \
    'target="${1:-}"' \
    'shift || true' \
    'cd /opt/syzkaller' \
    'case "$target" in' \
    '  descriptions) exec python3 /opt/syzkaller/tools/validate_task.py "$@" ;;' \
    '  all) python3 /opt/syzkaller/tools/validate_task.py; exec python3 -c "from pathlib import Path; Path(\"/opt/syzkaller/build.ok\").write_text(\"ok\\n\", encoding=\"utf-8\")" ;;' \
    '  *) echo "unsupported make target: $target" >&2; exit 2 ;;' \
    'esac' > /usr/local/bin/make \
    && chmod +x /usr/local/bin/make

COPY mini_syzkaller /opt/syzkaller
COPY rootfs/ /root/

WORKDIR /root

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

CMD ["bash", "-lc", "sleep infinity"]
