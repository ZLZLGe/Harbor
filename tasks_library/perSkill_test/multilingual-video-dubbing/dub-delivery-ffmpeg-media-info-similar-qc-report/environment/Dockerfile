FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY package_manifest.json /root/

RUN mkdir -p /root/delivery/segments /outputs /logs/verifier

RUN ffmpeg -y -f lavfi -i "sine=frequency=660:duration=1.66:sample_rate=48000" \
    -ac 1 /root/delivery/segments/seg_001.wav

RUN ffmpeg -y -f lavfi -i "sine=frequency=550:duration=2.21:sample_rate=48000" \
    -ac 1 /root/delivery/segments/seg_002.wav

RUN ffmpeg -y -f lavfi -i "sine=frequency=770:duration=1.17:sample_rate=48000" \
    -ac 1 /root/delivery/segments/seg_003.wav

RUN ffmpeg -y \
    -f lavfi -i "color=c=0x203040:s=1280x720:r=25:d=11" \
    -f lavfi -i "sine=frequency=220:duration=11:sample_rate=48000,volume=0.03" \
    -shortest \
    -c:v libx264 \
    -pix_fmt yuv420p \
    -c:a aac \
    -ar 48000 \
    -ac 1 \
    /tmp/base.mp4

RUN ffmpeg -y \
    -i /tmp/base.mp4 \
    -i /root/delivery/segments/seg_001.wav \
    -i /root/delivery/segments/seg_002.wav \
    -i /root/delivery/segments/seg_003.wav \
    -filter_complex "[1:a]adelay=1200|1200[s1];[2:a]adelay=4080|4080[s2];[3:a]adelay=7260|7260[s3];[0:a][s1][s2][s3]amix=inputs=4:duration=first:dropout_transition=0[outa]" \
    -map 0:v:0 \
    -map "[outa]" \
    -metadata:s:a:0 language=spa \
    -c:v copy \
    -c:a aac \
    -ar 48000 \
    -ac 1 \
    /root/delivery/final_mix.mp4

COPY skills /root/.codex/skills
