FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN dpkg --add-architecture i386 \
	&& apt-get update \
	&& apt-get install -y \
		build-essential \
		gcc-multilib \
		libc6-dev-i386 \
		linux-libc-dev \
		python3 \
		python3-pip \
	&& rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest==8.3.4

COPY assets /opt/task-assets

RUN install -D /opt/task-assets/mock-uapi/linux/dev_demo_compat.h /usr/include/linux/dev_demo_compat.h \
	&& mkdir -p /opt/syzkaller/sys/linux \
	&& printf '%s\n' \
		'include <linux/dev_demo_compat.h>' \
		'' \
		'resource fd_demo_compat[fd]' \
		'' \
		'syz_open_dev$demo_compat(dev ptr[in, string["/dev/demo_compat"]], id intptr, flags flags[open_flags]) fd_demo_compat' \
		'' \
		'demo_modes = DEMO_MODE_STRICT, DEMO_MODE_BULK' \
		'demo_flags = DEMO_FLAG_SHARED, DEMO_FLAG_TRACE' \
		'' \
		'demo_snapshot {' \
		'	slots	int32' \
		'	cookie	intptr' \
		'}' \
		'' \
		'demo_user_ref {' \
		'	token	int64' \
		'	user_ptr	intptr' \
		'}' \
		'' \
		'demo_window {' \
		'	index	int16' \
		'	count	int16' \
		'	snap	demo_snapshot' \
		'}' \
		'' \
		'demo_xact {' \
		'	opcode	int32' \
		'	flags	flags[demo_flags, int32]' \
		'	ref	demo_user_ref' \
		'}' \
		'' \
		'ioctl$DEMO_IOCTL_PEEK(fd fd_demo_compat, cmd const[DEMO_IOCTL_PEEK], arg ptr[out, demo_snapshot])' \
		'ioctl$DEMO_IOCTL_POKE(fd fd_demo_compat, cmd const[DEMO_IOCTL_POKE], arg ptr[in, demo_window])' \
		'ioctl$DEMO_IOCTL_XACT(fd fd_demo_compat, cmd const[DEMO_IOCTL_XACT], arg ptr[inout, demo_xact])' \
		'ioctl$DEMO_IOCTL_PING(fd fd_demo_compat, cmd const[DEMO_IOCTL_PING])' \
		> /opt/syzkaller/sys/linux/dev_demo_compat.txt \
	&& printf '%s\n' \
		'# Deliberately wrong starter file: size-sensitive ioctls were copied from amd64 only.' \
		'arches = amd64, 386' \
		'' \
		'DEMO_IOCTL_PEEK = 2148561184' \
		'DEMO_IOCTL_POKE = 1075343649' \
		'DEMO_IOCTL_XACT = 3222827298' \
		'DEMO_IOCTL_PING = 28963' \
		'DEMO_MODE_STRICT = 1' \
		'DEMO_MODE_BULK = 2' \
		'DEMO_FLAG_SHARED = 256' \
		'DEMO_FLAG_TRACE = 512' \
		> /opt/syzkaller/sys/linux/dev_demo_compat.txt.const

WORKDIR /root

COPY skills /root/.claude/skills
COPY skills /root/.codex/skills
COPY skills /root/.opencode/skill
COPY skills /root/.goose/skills
COPY skills /root/.factory/skills
COPY skills /root/.agents/skills
COPY skills /root/.gemini/skills

CMD ["bash", "-lc", "sleep infinity"]
