FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV SYZ_ENV=1

RUN apt-get update && apt-get install -y \
	ca-certificates \
	curl \
	git \
	make \
	golang-go \
	build-essential \
	python3 \
	python3-pip \
	&& rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest==8.3.4 pytest-json-ctrf==0.3.6

ARG SYZKALLER_COMMIT=c1f5c7d045a640603c66fb564b6c642adff4998a
RUN git clone https://github.com/google/syzkaller.git /opt/syzkaller \
	&& cd /opt/syzkaller \
	&& git checkout "$SYZKALLER_COMMIT"

COPY assets /task-assets

RUN cp /task-assets/dev_uinput.txt /opt/syzkaller/sys/linux/dev_uinput.txt \
	&& printf '# Fill the uinput constants for amd64 and 386 here.\narches = amd64, 386\n' > /opt/syzkaller/sys/linux/dev_uinput.txt.const

WORKDIR /root

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

CMD ["bash", "-lc", "sleep infinity"]
