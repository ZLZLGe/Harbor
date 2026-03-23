Write `/opt/syzkaller/sys/linux/dev_capring.txt` from the stream interface brief in `/root/capring_brief.md`.

The description must define the resource, opener, frame struct, specialized read and write syscalls, and every ioctl signature in the brief. Keep the output as one syzlang file. You may validate it with `cd /opt/syzkaller && make descriptions`.
