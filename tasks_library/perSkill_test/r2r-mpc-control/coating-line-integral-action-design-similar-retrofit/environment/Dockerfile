FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /root

COPY coating_line_cases.json /root/coating_line_cases.json
COPY coating_line_env.py /root/coating_line_env.py
COPY controller_scaffold.py /root/controller_scaffold.py
COPY skills /root/.codex/skills

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    pytest==8.4.1

CMD ["/bin/bash"]
