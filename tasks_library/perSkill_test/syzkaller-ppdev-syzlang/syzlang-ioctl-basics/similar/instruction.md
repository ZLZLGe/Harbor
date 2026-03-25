Write `/opt/syzkaller/sys/linux/dev_ppdiag.txt` for the parallel-port diagnostics interface described in `/root/ppdiag_brief.md`.

Your file must define the opener, resource, ioctl signatures, struct, and flag set from the brief with the correct pointer directions. Keep the output as a syzlang description file only. You may validate it with `cd /opt/syzkaller && make descriptions`.
