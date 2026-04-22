FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV NPM_CONFIG_REGISTRY=https://registry.npmjs.org/

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    git \
    jq \
    nodejs \
    npm \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN /usr/bin/npm install -g @openai/codex@0.120.0

RUN printf '#!/bin/bash\n\
set -e\n\
REAL_NPM=/usr/bin/npm\n\
if [ "$#" -ge 3 ] && [ "$1" = "install" ] && [ "$2" = "-g" ] && [[ "$3" == @openai/codex@* ]]; then\n\
  if command -v codex >/dev/null 2>&1; then\n\
    echo "Using preinstalled $(codex --version)"\n\
    exit 0\n\
  fi\n\
fi\n\
exec "$REAL_NPM" "$@"\n' > /usr/local/bin/npm && chmod +x /usr/local/bin/npm

RUN pip install pytest==8.3.3

RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY workspace /app/workspace
COPY skills /app/skills

RUN mkdir -p /app/output /logs/verifier /app/.codex/skills \
    && cp /app/workspace/launch_brief.md /app/launch_brief.md \
    && cp /app/workspace/channel_requirements.md /app/channel_requirements.md \
    && cp /app/workspace/voice_guide.md /app/voice_guide.md \
    && cp /app/workspace/build_bundle.py /app/build_bundle.py \
    && cp /app/workspace/data/fact_sheet.json /app/fact_sheet.json \
    && cp /app/workspace/data/keyword_plan.json /app/keyword_plan.json \
    && cp /app/workspace/data/source_notes.md /app/source_notes.md \
    && if [ -d /app/skills ] && [ -n "$(find /app/skills -mindepth 1 -maxdepth 1 -print -quit)" ]; then cp -R /app/skills/. /app/.codex/skills/; fi \
    && chmod 755 /root \
    && ln -sf /app/launch_brief.md /root/launch_brief.md \
    && ln -sf /app/channel_requirements.md /root/channel_requirements.md \
    && ln -sf /app/voice_guide.md /root/voice_guide.md \
    && ln -sf /app/build_bundle.py /root/build_bundle.py \
    && ln -sf /app/fact_sheet.json /root/fact_sheet.json \
    && ln -sf /app/keyword_plan.json /root/keyword_plan.json \
    && ln -sf /app/source_notes.md /root/source_notes.md \
    && touch /app/blog_post.md /app/linkedin_post.md /app/newsletter.json /app/seo_meta.json /app/publish_bundle.json \
    && ln -sf /app/blog_post.md /root/blog_post.md \
    && ln -sf /app/linkedin_post.md /root/linkedin_post.md \
    && ln -sf /app/newsletter.json /root/newsletter.json \
    && ln -sf /app/seo_meta.json /root/seo_meta.json \
    && ln -sf /app/publish_bundle.json /root/publish_bundle.json \
    && chown -R appuser:appuser /app /home/appuser /logs

ENV HOME=/home/appuser

USER appuser

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
