from __future__ import annotations

import hashlib
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from scapy.all import Ether, IP, Raw, TCP, wrpcap


CLIENT_MAC = "02:00:00:00:10:01"
SERVER_MAC = "02:00:00:00:20:01"
BASE_TIME = datetime(2025, 3, 8, 14, 0, 0, tzinfo=timezone.utc).timestamp()


def tls_client_hello(sni: str | None, *, seed: int) -> bytes:
    rng = random.Random(seed)
    random_bytes = bytes(rng.getrandbits(8) for _ in range(32))

    cipher_suites = bytes.fromhex("130113021303c02fc02b009c003c")
    compression_methods = b"\x01\x00"

    extensions = []
    if sni:
        host = sni.encode("ascii")
        name_entry = b"\x00" + len(host).to_bytes(2, "big") + host
        server_name_ext = b"\x00\x00" + (len(name_entry) + 2).to_bytes(2, "big") + len(name_entry).to_bytes(2, "big") + name_entry
        extensions.append(server_name_ext)

    supported_groups = b"\x00\x0a\x00\x08\x00\x06\x00\x17\x00\x1d\x00\x1e"
    point_formats = b"\x00\x0b\x00\x02\x01\x00"
    signature_algorithms = b"\x00\x0d\x00\x0e\x00\x0c\x04\x03\x05\x03\x06\x03\x08\x04\x08\x05\x08\x06"
    extensions.extend([supported_groups, point_formats, signature_algorithms])
    extensions_blob = b"".join(extensions)

    body = b"".join(
        [
            b"\x03\x03",
            random_bytes,
            b"\x00",
            len(cipher_suites).to_bytes(2, "big"),
            cipher_suites,
            compression_methods,
            len(extensions_blob).to_bytes(2, "big"),
            extensions_blob,
        ]
    )
    handshake = b"\x01" + len(body).to_bytes(3, "big") + body
    return b"\x16\x03\x01" + len(handshake).to_bytes(2, "big") + handshake


def tls_alert() -> bytes:
    return b"\x15\x03\x03\x00\x02\x02\x28"


def add_session(
    packets: list,
    *,
    when: float,
    client_ip: str,
    target_ip: str,
    target_port: int,
    client_port: int,
    sni: str | None,
    seed: int,
) -> None:
    payload = tls_client_hello(sni, seed=seed)
    server_reply = tls_alert()

    client_isn = 10000 + client_port
    server_isn = 40000 + client_port

    eth_c2s = Ether(src=CLIENT_MAC, dst=SERVER_MAC)
    eth_s2c = Ether(src=SERVER_MAC, dst=CLIENT_MAC)
    ip_c2s = IP(src=client_ip, dst=target_ip)
    ip_s2c = IP(src=target_ip, dst=client_ip)

    syn = eth_c2s / ip_c2s / TCP(sport=client_port, dport=target_port, flags="S", seq=client_isn)
    syn.time = when
    synack = eth_s2c / ip_s2c / TCP(sport=target_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    synack.time = when + 0.040
    ack = eth_c2s / ip_c2s / TCP(sport=client_port, dport=target_port, flags="A", seq=client_isn + 1, ack=server_isn + 1)
    ack.time = when + 0.080

    req = eth_c2s / ip_c2s / TCP(sport=client_port, dport=target_port, flags="PA", seq=client_isn + 1, ack=server_isn + 1) / Raw(load=payload)
    req.time = when + 0.150

    ack2 = eth_s2c / ip_s2c / TCP(sport=target_port, dport=client_port, flags="A", seq=server_isn + 1, ack=client_isn + 1 + len(payload))
    ack2.time = when + 0.190

    resp = (
        eth_s2c
        / ip_s2c
        / TCP(sport=target_port, dport=client_port, flags="PA", seq=server_isn + 1, ack=client_isn + 1 + len(payload))
        / Raw(load=server_reply)
    )
    resp.time = when + 0.260

    ack3 = eth_c2s / ip_c2s / TCP(sport=client_port, dport=target_port, flags="A", seq=client_isn + 1 + len(payload), ack=server_isn + 1 + len(server_reply))
    ack3.time = when + 0.300

    fin1 = eth_c2s / ip_c2s / TCP(
        sport=client_port,
        dport=target_port,
        flags="FA",
        seq=client_isn + 1 + len(payload),
        ack=server_isn + 1 + len(server_reply),
    )
    fin1.time = when + 0.360
    fin2 = eth_s2c / ip_s2c / TCP(
        sport=target_port,
        dport=client_port,
        flags="FA",
        seq=server_isn + 1 + len(server_reply),
        ack=client_isn + 2 + len(payload),
    )
    fin2.time = when + 0.410
    last_ack = eth_c2s / ip_c2s / TCP(
        sport=client_port,
        dport=target_port,
        flags="A",
        seq=client_isn + 2 + len(payload),
        ack=server_isn + 2 + len(server_reply),
    )
    last_ack.time = when + 0.450

    packets.extend([syn, synack, ack, req, ack2, resp, ack3, fin1, fin2, last_ack])


def seed_for(*parts: object) -> int:
    data = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(data).digest()[:4], "big")


def emit_group(
    packets: list,
    *,
    offsets: list[int],
    client_ip: str,
    target_ip: str,
    target_port: int,
    sni: str | None,
    client_port_start: int,
) -> None:
    for idx, offset in enumerate(offsets):
        add_session(
            packets,
            when=BASE_TIME + offset,
            client_ip=client_ip,
            target_ip=target_ip,
            target_port=target_port,
            client_port=client_port_start + idx,
            sni=sni,
            seed=seed_for(client_ip, target_ip, target_port, sni or "none", idx),
        )


def main(output_path: str) -> None:
    packets = []

    emit_group(
        packets,
        offsets=[11, 71, 132, 191, 251, 312],
        client_ip="10.77.0.21",
        target_ip="198.51.100.20",
        target_port=443,
        sni="api.sync-node.net",
        client_port_start=41000,
    )
    emit_group(
        packets,
        offsets=[24, 114, 203, 294, 384],
        client_ip="10.77.0.44",
        target_ip="203.0.113.77",
        target_port=443,
        sni="edge-pulse.backhaul.org",
        client_port_start=42000,
    )

    emit_group(
        packets,
        offsets=[30, 88, 149, 227, 301],
        client_ip="10.77.0.55",
        target_ip="203.0.113.88",
        target_port=443,
        sni="portal.office.example",
        client_port_start=43000,
    )
    emit_group(
        packets,
        offsets=[40, 100, 160, 220],
        client_ip="10.77.0.62",
        target_ip="198.51.100.60",
        target_port=443,
        sni="status.mesh.example",
        client_port_start=44000,
    )
    emit_group(
        packets,
        offsets=[15, 75, 135, 195, 255, 315],
        client_ip="10.77.0.70",
        target_ip="198.51.100.70",
        target_port=443,
        sni=None,
        client_port_start=45000,
    )

    benign_singletons = [
        (7, "10.77.0.10", "198.51.100.10", "www.portal.example", 46000),
        (52, "10.77.0.11", "198.51.100.11", "login.mail.example", 46010),
        (166, "10.77.0.12", "203.0.113.15", "cdn.assets.example", 46020),
        (248, "10.77.0.13", "203.0.113.25", "support.docs.example", 46030),
        (333, "10.77.0.14", "198.51.100.25", "backup.client.example", 46040),
    ]
    for offset, client_ip, target_ip, sni, client_port in benign_singletons:
        add_session(
            packets,
            when=BASE_TIME + offset,
            client_ip=client_ip,
            target_ip=target_ip,
            target_port=443,
            client_port=client_port,
            sni=sni,
            seed=seed_for(client_ip, target_ip, client_port, sni),
        )

    packets.sort(key=lambda pkt: float(pkt.time))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    wrpcap(str(output), packets)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: generate_tls_handshake_mix.py OUTPUT_PCAP")
    main(sys.argv[1])
