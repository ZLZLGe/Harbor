FROM jasonish/suricata:7.0.11

ENV PYTHONUNBUFFERED=1

WORKDIR /root

COPY . /tmp/task_env

RUN cp /tmp/task_env/suricata.yaml /root/suricata.yaml \
    && if [ -f /tmp/task_env/local.rules ]; then cp /tmp/task_env/local.rules /root/local.rules; fi \
    && if [ -d /tmp/task_env/rules ]; then mkdir -p /root/rules && cp -r /tmp/task_env/rules/. /root/rules/; fi \
    && if [ -d /tmp/task_env/data ]; then mkdir -p /root/data && cp -r /tmp/task_env/data/. /root/data/; fi \
    && if [ -d /tmp/task_env/pcaps ]; then mkdir -p /root/pcaps && cp -r /tmp/task_env/pcaps/. /root/pcaps/; fi \
    && rm -rf /tmp/task_env

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

ENTRYPOINT []
CMD ["bash", "-lc", "sleep infinity"]
