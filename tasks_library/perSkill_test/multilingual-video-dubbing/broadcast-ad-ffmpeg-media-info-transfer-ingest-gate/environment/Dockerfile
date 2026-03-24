FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY ingest_requirements.json /root/ingest_requirements.json

RUN mkdir -p /root/candidates

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1920x1080:rate=25 \
    -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
    -t 20 \
    -c:v libx264 -pix_fmt yuv420p \
    -c:a aac -b:a 192k \
    /root/candidates/spot_A_duration_20s.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1280x720:rate=25 \
    -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
    -t 15 \
    -c:v libx264 -pix_fmt yuv420p \
    -c:a aac -b:a 192k \
    /root/candidates/spot_B_resolution_720p.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1920x1080:rate=30000/1001 \
    -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
    -t 15 \
    -c:v libx264 -pix_fmt yuv420p \
    -c:a aac -b:a 192k \
    /root/candidates/spot_C_frame_rate_2997.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1920x1080:rate=25 \
    -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
    -t 15 \
    -c:v libx264 -pix_fmt yuv420p \
    -c:a pcm_s16le \
    /root/candidates/spot_D_audio_pcm.mov

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1920x1080:rate=25 \
    -f lavfi -i anullsrc=channel_layout=mono:sample_rate=48000 \
    -t 15 \
    -c:v mpeg4 \
    -c:a aac -b:a 128k \
    /root/candidates/spot_E_video_mpeg4_mono.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=1920x1080:rate=25 \
    -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 \
    -t 15 \
    -c:v libx264 -pix_fmt yuv420p \
    -c:a aac -b:a 192k \
    /root/candidates/spot_F_master_ok.mp4

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

RUN mkdir -p /logs/verifier
