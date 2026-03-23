import argparse
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap


def mk_request(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
    merged_headers = {
        "Host": "cdn.local",
        "Content-Length": str(len(body)),
        "Connection": "close",
        **headers,
    }
    header_lines = b"\r\n".join(f"{key}: {value}".encode() for key, value in merged_headers.items())
    return b"".join([f"{method} {path} HTTP/1.1\r\n".encode(), header_lines, b"\r\n\r\n", body])


def build_tcp_session_pcap(out_path: Path, request: bytes, *, client_port: int) -> None:
    client_ip = "10.30.0.10"
    server_ip = "10.30.0.20"
    server_port = 8080
    client_isn = 21000
    server_isn = 25000

    eth = Ether(src="02:00:00:00:00:51", dst="02:00:00:00:00:52")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    syn = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn)
    synack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    ack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1)

    header_end = request.find(b"\r\n\r\n")
    split1 = max(1, header_end // 2) if header_end != -1 else max(1, len(request) // 3)
    split2 = min(len(request) - 1, header_end + 8) if header_end != -1 else max(split1 + 1, (2 * len(request)) // 3)
    chunks = [request[:split1], request[split1:split2], request[split2:]]

    packets = [syn, synack, ack]
    seq = client_isn + 1
    for chunk in chunks:
        if not chunk:
            continue
        packets.append(eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq, ack=server_isn + 1) / Raw(load=chunk))
        seq += len(chunk)

    req_len = sum(len(chunk) for chunk in chunks)
    packets.append(eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=server_isn + 1, ack=client_isn + 1 + req_len))
    response = b"HTTP/1.1 204 No Content\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    packets.append(
        eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="PA", seq=server_isn + 1, ack=client_isn + 1 + req_len) / Raw(load=response)
    )
    wrpcap(str(out_path), packets)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    pos_uri = "/cdn/diag/pull?node=1a2b3c4d&ticket=123456789012&region=apac"
    neg_uri = "/cdn/diag/pull?node=1a2b3c4d&ticket=123456789012&region=apac"

    build_tcp_session_pcap(
        out_dir / "train_pos.pcap",
        mk_request("GET", pos_uri, {"x-pull-mode": "stage"}, b""),
        client_port=28001,
    )
    build_tcp_session_pcap(
        out_dir / "train_neg.pcap",
        mk_request("GET", neg_uri, {"x-pull-mode": "prod"}, b""),
        client_port=28002,
    )


if __name__ == "__main__":
    main()
