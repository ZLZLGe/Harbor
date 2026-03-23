Write `/opt/syzkaller/sys/linux/dev_sensorhub_ctl.txt` using the interface brief in `/root/sensorhub_brief.md`.

The description must include the resource, opener, flag set, both structs, and every ioctl signature listed in the brief with the correct pointer directions. Keep the output as one syzlang file. You may validate it with `cd /opt/syzkaller && make descriptions`.
