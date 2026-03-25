from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from scapy.all import Ether, IP, Raw, TCP, wrpcap


SERVER_IP = "10.80.1.7"
SERVER_MAC = "02:00:00:00:66:67"
CLIENT_MAC = "02:00:00:00:10:01"
BASE_TIME = datetime(2025, 2, 14, 8, 10, 0, tzinfo=timezone.utc).timestamp()


def client_line(text: str) -> tuple[str, str]:
    return ("client", text + "\r\n")


def server_line(text: str) -> tuple[str, str]:
    return ("server", text + "\r\n")


def build_session(
    *,
    client_ip: str,
    client_port: int,
    start_offset: float,
    server_port: int,
    transcript: list[tuple[float, str, str]],
) -> list:
    packets = []

    client_isn = 10000 + client_port
    server_isn = 50000 + client_port
    client_seq = client_isn + 1
    server_seq = server_isn + 1

    eth_c2s = Ether(src=CLIENT_MAC, dst=SERVER_MAC)
    eth_s2c = Ether(src=SERVER_MAC, dst=CLIENT_MAC)
    ip_c2s = IP(src=client_ip, dst=SERVER_IP)
    ip_s2c = IP(src=SERVER_IP, dst=client_ip)

    start_time = BASE_TIME + start_offset

    syn = eth_c2s / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn)
    syn.time = start_time
    synack = eth_s2c / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    synack.time = start_time + 0.050
    ack = eth_c2s / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_seq, ack=server_seq)
    ack.time = start_time + 0.100
    packets.extend([syn, synack, ack])

    for offset, sender, text in transcript:
        payload = text.encode("utf-8")
        when = BASE_TIME + offset
        if sender == "client":
            pkt = (
                eth_c2s
                / ip_c2s
                / TCP(sport=client_port, dport=server_port, flags="PA", seq=client_seq, ack=server_seq)
                / Raw(load=payload)
            )
            pkt.time = when
            client_seq += len(payload)

            ack_pkt = eth_s2c / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=server_seq, ack=client_seq)
            ack_pkt.time = when + 0.015
        else:
            pkt = (
                eth_s2c
                / ip_s2c
                / TCP(sport=server_port, dport=client_port, flags="PA", seq=server_seq, ack=client_seq)
                / Raw(load=payload)
            )
            pkt.time = when
            server_seq += len(payload)

            ack_pkt = eth_c2s / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_seq, ack=server_seq)
            ack_pkt.time = when + 0.015

        packets.extend([pkt, ack_pkt])

    fin_time = BASE_TIME + transcript[-1][0] + 0.200
    fin1 = eth_c2s / ip_c2s / TCP(sport=client_port, dport=server_port, flags="FA", seq=client_seq, ack=server_seq)
    fin1.time = fin_time
    fin2 = eth_s2c / ip_s2c / TCP(sport=server_port, dport=client_port, flags="FA", seq=server_seq, ack=client_seq + 1)
    fin2.time = fin_time + 0.030
    last_ack = eth_c2s / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_seq + 1, ack=server_seq + 1)
    last_ack.time = fin_time + 0.060
    packets.extend([fin1, fin2, last_ack])

    return packets


def main(output_path: str) -> None:
    sessions = [
        build_session(
            client_ip="10.80.0.10",
            client_port=50010,
            start_offset=1.0,
            server_port=6667,
            transcript=[
                (2.0, *client_line("NICK alice")),
                (2.4, *client_line("USER alice 0 * :Alice")),
                (2.8, *server_line(":relay.example.net 001 alice :Welcome to RelayNet")),
                (3.4, *client_line("JOIN #general")),
                (4.0, *server_line(":alice!user@10.80.0.10 JOIN #general")),
                (4.8, *client_line("PRIVMSG #general :morning all")),
                (5.3, *server_line(":bob!user@10.80.0.11 PRIVMSG #general :standup in ten")),
                (6.1, *client_line("PRIVMSG #general :copy that")),
                (7.0, *server_line("PING :relay.example.net")),
                (7.3, *client_line("PONG relay.example.net")),
            ],
        ),
        build_session(
            client_ip="10.80.0.21",
            client_port=50021,
            start_offset=8.0,
            server_port=6667,
            transcript=[
                (9.0, *client_line("NICK opslead")),
                (9.4, *client_line("USER opslead 0 * :Ops Lead")),
                (9.8, *server_line(":relay.example.net 001 opslead :Welcome to RelayNet")),
                (10.6, *client_line("PRIVMSG deploybot :!status")),
                (10.9, *server_line(":deploybot!bot@relay PRIVMSG opslead :green")),
                (11.8, *client_line("PRIVMSG deploybot :!reload")),
                (12.1, *server_line(":deploybot!bot@relay PRIVMSG opslead :denied: maintenance window")),
                (12.9, *client_line("PRIVMSG #ops :deploy freeze is still active")),
            ],
        ),
        build_session(
            client_ip="10.80.0.44",
            client_port=50044,
            start_offset=15.0,
            server_port=6667,
            transcript=[
                (16.0, *client_line("NICK auditop")),
                (16.4, *client_line("USER auditop 0 * :Audit Operator")),
                (16.8, *server_line(":relay.example.net 001 auditop :Welcome to RelayNet")),
                (17.4, *server_line("PING :relay.example.net")),
                (17.7, *client_line("PONG relay.example.net")),
                (84.0, *client_line("PRIVMSG node42 :!id")),
                (85.0, *server_line(":node42!svc@relay PRIVMSG auditop :uid=0(root) gid=0(root) groups=0(root)")),
                (122.0, *client_line("PRIVMSG node42 :!pwd")),
                (123.0, *server_line(":node42!svc@relay PRIVMSG auditop :/srv/.cache")),
                (160.0, *client_line("PRIVMSG node42 :!exfil plans.txt 96")),
                (162.0, *server_line(":node42!svc@relay PRIVMSG auditop :READY plans.txt chunks=3")),
                (190.0, *client_line("PRIVMSG node42 :!sleep 45")),
                (191.0, *server_line(":node42!svc@relay PRIVMSG auditop :OK sleep=45")),
                (192.0, *server_line("PING :relay.example.net")),
                (192.2, *client_line("PONG relay.example.net")),
            ],
        ),
        build_session(
            client_ip="10.80.0.52",
            client_port=50052,
            start_offset=20.0,
            server_port=6667,
            transcript=[
                (21.0, *client_line("NICK carol")),
                (21.4, *client_line("USER carol 0 * :Carol")),
                (21.8, *server_line(":relay.example.net 001 carol :Welcome to RelayNet")),
                (22.5, *client_line("JOIN #random")),
                (23.1, *server_line(":carol!user@10.80.0.52 JOIN #random")),
                (24.0, *server_line(":dave!user@10.80.0.53 PRIVMSG #random :if only we could !sleep through patch Tuesday")),
                (25.0, *client_line("PRIVMSG #random :not with this pager")),
            ],
        ),
    ]

    packets = []
    for session_packets in sessions:
        packets.extend(session_packets)
    packets.sort(key=lambda pkt: float(pkt.time))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    wrpcap(str(output), packets)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: generate_irc_mix_pcap.py OUTPUT_PCAP")
    main(sys.argv[1])
