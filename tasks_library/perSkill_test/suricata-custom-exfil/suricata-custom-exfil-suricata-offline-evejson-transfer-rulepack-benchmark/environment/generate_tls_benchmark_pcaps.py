import argparse
import hashlib
from pathlib import Path

from scapy.all import Ether, IP, TCP, Raw, wrpcap


SAMPLES = [
    ("atlas-sync-a.pcap", "sync-node-a.storage-relay.net"),
    ("boreal-sync-b.pcap", "sync-node-b.storage-relay.net"),
    ("cirrus-archive.pcap", "api.backup-cab.net"),
    ("dune-cache.pcap", "north-cache.storage-relay.net"),
    ("ember-login.pcap", "login.storage-relay.net"),
    ("fern-updates.pcap", "updates.safevendor.net"),
    ("glacier-proxy.pcap", "cdn.backup-cab.net.safevendor.org"),
]


def tls_client_hello(hostname: str) -> bytes:
    host_bytes = hostname.encode("ascii")
    random_bytes = hashlib.sha256(host_bytes).digest()[:32]

    server_name = b"\x00" + len(host_bytes).to_bytes(2, "big") + host_bytes
    sni_body = len(server_name).to_bytes(2, "big") + server_name
    sni_ext = b"\x00\x00" + len(sni_body).to_bytes(2, "big") + sni_body

    groups_body = b"\x00\x04\x00\x1d\x00\x17"
    groups_ext = b"\x00\x0a" + len(groups_body).to_bytes(2, "big") + groups_body

    ec_point_body = b"\x01\x00"
    ec_point_ext = b"\x00\x0b" + len(ec_point_body).to_bytes(2, "big") + ec_point_body

    extensions = sni_ext + groups_ext + ec_point_ext
    cipher_suites = b"\x13\x01\x13\x02\xc0\x2f"

    hello_body = b"".join(
        [
            b"\x03\x03",
            random_bytes,
            b"\x00",
            len(cipher_suites).to_bytes(2, "big"),
            cipher_suites,
            b"\x01\x00",
            len(extensions).to_bytes(2, "big"),
            extensions,
        ]
    )

    handshake = b"\x01" + len(hello_body).to_bytes(3, "big") + hello_body
    return b"\x16\x03\x01" + len(handshake).to_bytes(2, "big") + handshake


def build_packets(payload: bytes, *, client_port: int, client_ip: str, server_ip: str) -> list:
    server_port = 443
    client_isn = 100000 + client_port
    server_isn = 300000 + client_port

    eth = Ether(src="02:00:00:00:50:01", dst="02:00:00:00:50:02")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    packets = [
        eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn),
        eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1),
        eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1),
    ]

    split_1 = max(1, len(payload) // 3)
    split_2 = max(split_1 + 1, (2 * len(payload)) // 3)
    chunks = [payload[:split_1], payload[split_1:split_2], payload[split_2:]]

    seq = client_isn + 1
    for chunk in chunks:
        if not chunk:
            continue
        packets.append(
            eth
            / ip_c2s
            / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq, ack=server_isn + 1)
            / Raw(load=chunk)
        )
        seq += len(chunk)

    request_len = sum(len(chunk) for chunk in chunks)
    packets.append(
        eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=server_isn + 1, ack=client_isn + 1 + request_len)
    )

    server_alert = b"\x15\x03\x03\x00\x02\x02\x28"
    packets.append(
        eth
        / ip_s2c
        / TCP(sport=server_port, dport=client_port, flags="PA", seq=server_isn + 1, ack=client_isn + 1 + request_len)
        / Raw(load=server_alert)
    )

    response_len = len(server_alert)
    packets.append(
        eth
        / ip_c2s
        / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1 + request_len, ack=server_isn + 1 + response_len)
    )
    packets.append(
        eth
        / ip_c2s
        / TCP(sport=client_port, dport=server_port, flags="FA", seq=client_isn + 1 + request_len, ack=server_isn + 1 + response_len)
    )
    packets.append(
        eth
        / ip_s2c
        / TCP(sport=server_port, dport=client_port, flags="FA", seq=server_isn + 1 + response_len, ack=client_isn + 2 + request_len)
    )
    packets.append(
        eth
        / ip_c2s
        / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 2 + request_len, ack=server_isn + 2 + response_len)
    )

    return packets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for index, (filename, hostname) in enumerate(SAMPLES):
        packets = build_packets(
            tls_client_hello(hostname),
            client_port=24000 + index,
            client_ip=f"10.90.{index}.10",
            server_ip=f"10.91.{index}.20",
        )
        wrpcap(str(out_dir / filename), packets)


if __name__ == "__main__":
    main()
