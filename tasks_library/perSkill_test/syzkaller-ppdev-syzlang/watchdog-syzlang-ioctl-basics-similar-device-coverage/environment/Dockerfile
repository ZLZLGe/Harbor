FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV SYZ_ENV=1

RUN apt-get update && apt-get install -y \
	ca-certificates \
	git \
	make \
	golang-go \
	build-essential \
	linux-libc-dev \
	python3 \
	python3-pip \
	&& rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest==8.3.4

ARG SYZKALLER_COMMIT=c1f5c7d045a640603c66fb564b6c642adff4998a
RUN git clone https://github.com/google/syzkaller.git /opt/syzkaller \
	&& cd /opt/syzkaller \
	&& git checkout "$SYZKALLER_COMMIT" \
	&& : > /opt/syzkaller/sys/linux/dev_watchdog_ctl.txt \
	&& : > /opt/syzkaller/sys/linux/dev_watchdog_ctl.txt.const

COPY assets /task-assets
COPY skills /root/.codex/skills

WORKDIR /root

CMD ["bash", "-lc", "sleep infinity"]
