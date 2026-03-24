FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY evidence_batch.json /root/evidence_batch.json

RUN mkdir -p /root/evidence/bodycam /root/evidence/cctv /logs/verifier

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1280x720:rate=30 \
    -f lavfi -i sine=frequency=880:sample_rate=48000 \
    -t 12 \
    -c:v libx264 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -ac 1 \
    /root/evidence/bodycam/officer12_primary.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1280x720:rate=30 \
    -t 12 \
    -c:v libx264 -pix_fmt yuv420p \
    /root/evidence/bodycam/officer12_noaudio.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1280x720:rate=30 \
    -f lavfi -i sine=frequency=660:sample_rate=48000 \
    -t 8.7 \
    -c:v libx264 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -ac 1 \
    /root/evidence/bodycam/officer19_truncated.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=960x540:rate=30 \
    -f lavfi -i sine=frequency=520:sample_rate=48000 \
    -t 12.04 \
    -c:v libx264 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -ac 1 \
    /root/evidence/bodycam/officer41_lowres.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1280x720:rate=30 \
    -f lavfi -i sine=frequency=410:sample_rate=48000 \
    -t 12.04 \
    -c:v mpeg4 \
    -c:a libmp3lame -b:a 128k -ac 1 \
    /root/evidence/cctv/garage_export.avi

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1280x720:rate=30 \
    -f lavfi -i sine=frequency=300:sample_rate=48000 \
    -t 11.96 \
    -c:v libx264 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -ac 1 \
    /root/evidence/cctv/lobby_overview.mp4

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills
