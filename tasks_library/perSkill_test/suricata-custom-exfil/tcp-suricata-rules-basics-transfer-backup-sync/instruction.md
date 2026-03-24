You are reviewing a proprietary backup synchronization channel carried over raw TCP.

Write Suricata rule(s) in `/root/tcp_backup_sync.rules` so that Suricata raises an alert with `sid:1000001` only when all of the following are true in the reassembled client-to-server stream:

1. The destination port is TCP `4040`
2. The stream contains the line `SYNC/3`
3. The stream contains the line `MODE: MIRROR`
4. The stream contains the line `DEST: vault`
5. The stream contains `PAYLOAD=` followed by at least 128 hexadecimal characters
6. The stream contains `TOKEN=` followed by exactly 32 hexadecimal characters

You will find packet captures in `/root/pcaps/` and the Suricata config at `/root/suricata.yaml`.

Avoid false positives: traffic that misses any one of the conditions above must not alert.
