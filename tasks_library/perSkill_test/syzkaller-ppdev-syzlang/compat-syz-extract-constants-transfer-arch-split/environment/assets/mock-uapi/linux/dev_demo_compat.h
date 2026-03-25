#ifndef _LINUX_DEV_DEMO_COMPAT_H
#define _LINUX_DEV_DEMO_COMPAT_H

#include <linux/types.h>
#include <sys/ioctl.h>

#define DEMO_COMPAT_IOC_MAGIC 'q'

struct demo_snapshot {
	__u32 slots;
	unsigned long cookie;
};

struct demo_user_ref {
	__u64 token;
	void *user_ptr;
};

struct demo_window {
	__u16 index;
	__u16 count;
	struct demo_snapshot snap;
};

struct demo_xact {
	__u32 opcode;
	__u32 flags;
	struct demo_user_ref ref;
};

#define DEMO_MODE_STRICT (1U << 0)
#define DEMO_MODE_BULK (1U << 1)
#define DEMO_FLAG_SHARED (1U << 8)
#define DEMO_FLAG_TRACE (1U << 9)

#define DEMO_IOCTL_PEEK _IOR(DEMO_COMPAT_IOC_MAGIC, 0x20, struct demo_snapshot)
#define DEMO_IOCTL_POKE _IOW(DEMO_COMPAT_IOC_MAGIC, 0x21, struct demo_window)
#define DEMO_IOCTL_XACT _IOWR(DEMO_COMPAT_IOC_MAGIC, 0x22, struct demo_xact)
#define DEMO_IOCTL_PING _IO(DEMO_COMPAT_IOC_MAGIC, 0x23)

#endif
