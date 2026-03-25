Create `/opt/syzkaller/sys/linux/dev_ppdiag.txt.const` for the existing syzlang description at `/opt/syzkaller/sys/linux/dev_ppdiag.txt`.

Use the notes in `/root/ppdiag_constants_brief.md`. The file must declare `arches = amd64, 386` and define every ioctl number and mode flag used by the description. Keep the output as a `.txt.const` file only. You may validate it with `cd /opt/syzkaller && make descriptions`.
