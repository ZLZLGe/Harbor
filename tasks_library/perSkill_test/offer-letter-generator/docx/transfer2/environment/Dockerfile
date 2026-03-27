FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
    python-docx==1.1.2 \
    pytest==8.3.4

WORKDIR /root

COPY offer_letter_template.docx /root/offer_letter_template.docx
COPY profile_core.json /root/profile_core.json
COPY offer_terms.json /root/offer_terms.json

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

CMD ["/bin/bash"]
