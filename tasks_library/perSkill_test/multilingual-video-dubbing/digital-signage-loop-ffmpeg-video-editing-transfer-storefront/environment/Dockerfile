FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY storefront_plan.json /tmp/task-assets/

RUN ffmpeg -y -loglevel error \
    -f lavfi -i testsrc2=size=854x480:rate=30 \
    -f lavfi -i sine=frequency=660:sample_rate=44100:duration=3.6 \
    -t 3.6 \
    -vf "eq=saturation=1.25:contrast=1.08,drawbox=x='mod(t*150,700)':y=40:w=90:h=90:color=red@0.75:t=fill" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -ar 44100 -ac 2 \
    /root/espresso_hero.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i smptebars=size=720x1280:rate=24 \
    -f lavfi -i sine=frequency=523:sample_rate=32000:duration=1.8 \
    -t 1.8 \
    -vf "rotate='0.03*sin(2*PI*t)':fillcolor=black,eq=brightness=0.04:saturation=1.10,drawbox=x=80:y='mod(t*220,980)':w=180:h=180:color=yellow@0.70:t=fill" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 96k -ar 32000 -ac 1 \
    /root/pastry_vertical.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i color=size=640x640:rate=15:color=0x18324d \
    -f lavfi -i sine=frequency=784:sample_rate=22050:duration=2.1 \
    -t 2.1 \
    -vf "drawgrid=width=80:height=80:thickness=4:color=white@0.55,drawbox=x='mod(t*180,520)':y='mod(t*130,520)':w=120:h=120:color=green@0.85:t=fill" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 96k -ar 22050 -ac 2 \
    /root/loyalty_square.mp4

RUN ffmpeg -y -loglevel error \
    -f lavfi -i rgbtestsrc=size=1024x576:rate=25 \
    -f lavfi -i sine=frequency=349:sample_rate=48000:duration=4.4 \
    -t 4.4 \
    -vf "hflip,boxblur=2:1,eq=gamma=1.10:saturation=0.85,drawbox=x='mod(t*200,760)':y=400:w=180:h=120:color=cyan@0.75:t=fill" \
    -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
    -c:a aac -b:a 128k -ar 48000 -ac 1 \
    /root/evening_special.mp4

RUN cp /tmp/task-assets/storefront_plan.json /root/storefront_plan.json

COPY skills /root/.codex/skills

RUN mkdir -p /outputs /logs/verifier /tmp/storefront-work
