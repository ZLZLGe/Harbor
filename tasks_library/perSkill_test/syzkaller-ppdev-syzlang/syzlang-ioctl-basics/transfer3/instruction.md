Write `/opt/syzkaller/sys/linux/dev_bridge_port.txt` from the bridge control brief in `/root/bridge_port_brief.md`.

The description must include the resource, opener, flag set, and all ioctl signatures from the brief. Use the correct pointer directions and the required `ifreq_t` forms. Keep the output as one syzlang file. You may validate it with `cd /opt/syzkaller && make descriptions`.
