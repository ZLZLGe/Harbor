FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/root
ENV MEDIA_PICK_FRAME_TOOL=/usr/local/bin/media-pick-frame

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        coreutils \
        curl \
        ffmpeg \
        findutils \
        gawk \
        grep \
        nodejs \
        npm \
        sed \
        tini \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir pillow numpy

RUN mkdir -p /root/media_pick/input /root/media_pick/output /root/.codex/skills /logs/verifier

COPY data /root/media_pick/input
COPY . /tmp/task-environment
COPY skills /root/.codex/skills

RUN cd /root/media_pick/input \
    && find . -type f -print0 | sort -z | xargs -0 sha256sum > /opt/media-pick-input.sha256 \
    && if [ -f /root/.codex/skills/video-frames/scripts/frame.sh ]; then chmod 755 /root/.codex/skills/video-frames/scripts/frame.sh && ln -sf /root/.codex/skills/video-frames/scripts/frame.sh /usr/local/bin/media-pick-frame; fi \
    && chmod 644 /opt/media-pick-input.sha256 \
    && chmod 777 /root/media_pick/output

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
