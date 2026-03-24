import argparse
import random
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap


def deterministic_hex(n: int, *, seed: int, uppercase: bool = False) -> str:
    alphabet = "0123456789ABCDEF" if uppercase else "0123456789abcdef"
    r = random.Random(seed)
    return "".join(r.choice(alphabet) for _ in range(n))


def build_message(lines: list[str], *, sep: bytes) -> bytes:
    return sep.join(line.encode() for line in lines) + sep


def build_tcp_session_pcap(
    out_path: Path,
    payload: bytes,
    *,
    client_port: int,
    server_port: int,
) -> None:
    client_ip = "172.20.0.10"
    server_ip = "172.20.0.40"

    client_isn = 13000
    server_isn = 41000

    eth = Ether(src="02:20:00:00:00:01", dst="02:20:00:00:00:02")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    syn = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn)
    synack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    ack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1)

    cut1 = max(1, len(payload) // 4)
    cut2 = max(cut1 + 1, len(payload) // 2)
    cut3 = max(cut2 + 1, (3 * len(payload)) // 4)
    chunks = [payload[:cut1], payload[cut1:cut2], payload[cut2:cut3], payload[cut3:]]

    req_packets = []
    seq = client_isn + 1
    for chunk in chunks:
        if not chunk:
            continue
        req_packets.append(
            eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq, ack=server_isn + 1) / Raw(load=chunk)
        )
        seq += len(chunk)

    req_len = sum(len(chunk) for chunk in chunks)
    ack2 = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=server_isn + 1, ack=client_isn + 1 + req_len)

    response = b"SYNC-ACK\nSTATUS: queued\n"
    resp = (
        eth
        / ip_s2c
        / TCP(sport=server_port, dport=client_port, flags="PA", seq=server_isn + 1, ack=client_isn + 1 + req_len)
        / Raw(load=response)
    )
    resp_len = len(response)

    ack3 = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1 + req_len, ack=server_isn + 1 + resp_len)
    fin1 = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="FA", seq=client_isn + 1 + req_len, ack=server_isn + 1 + resp_len)
    finack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="FA", seq=server_isn + 1 + resp_len, ack=client_isn + 2 + req_len)
    lastack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 2 + req_len, ack=server_isn + 2 + resp_len)

    packets = [syn, synack, ack, *req_packets, ack2, resp, ack3, fin1, finack, lastack]
    wrpcap(str(out_path), packets)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    payload_ok = deterministic_hex(160, seed=17)
    token_ok = deterministic_hex(32, seed=23, uppercase=True)

    positive = build_message(
        [
            "SYNC/3",
            "MODE: MIRROR",
            "DEST: vault",
            "WINDOW: nightly",
            f"PAYLOAD={payload_ok}",
            f"TOKEN={token_ok}",
        ],
        sep=b"\n",
    )

    negative = build_message(
        [
            "SYNC/3",
            "MODE: MIRROR",
            "DEST: archive",
            "WINDOW: nightly",
            f"PAYLOAD={payload_ok}",
            f"TOKEN={token_ok}",
        ],
        sep=b"\n",
    )

    build_tcp_session_pcap(out_dir / "backup_match.pcap", positive, client_port=25040, server_port=4040)
    build_tcp_session_pcap(out_dir / "backup_benign.pcap", negative, client_port=25041, server_port=4040)


if __name__ == "__main__":
    main()
