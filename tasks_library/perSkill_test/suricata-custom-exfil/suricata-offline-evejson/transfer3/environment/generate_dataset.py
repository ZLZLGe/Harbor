import argparse
import random
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap


def deterministic_hex(n: int, seed: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def mk_request(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
    base_headers = {
        "Content-Length": str(len(body)),
        "Connection": "close",
        **headers,
    }
    header_lines = b"\r\n".join([f"{key}: {value}".encode() for key, value in base_headers.items()])
    return b"".join(
        [
            f"{method} {path} HTTP/1.1\r\n".encode(),
            b"Host: example.com\r\n",
            header_lines,
            b"\r\n",
            b"\r\n",
            body,
        ]
    )


def build_http_session_packets(request: bytes, *, client_ip: str, server_ip: str, client_port: int, server_port: int) -> list:
    client_isn = 14000 + client_port
    server_isn = 24000 + server_port + client_port

    eth = Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    syn = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn)
    synack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    ack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1)

    header_end = request.find(b"\r\n\r\n")
    if header_end != -1:
        split1 = max(1, header_end // 2)
        split2 = min(len(request) - 1, header_end + 12)
        chunks = [request[:split1], request[split1:split2], request[split2:]]
    else:
        split1 = max(1, len(request) // 3)
        split2 = max(split1 + 1, (2 * len(request)) // 3)
        chunks = [request[:split1], request[split1:split2], request[split2:]]

    packets = [syn, synack, ack]
    seq = client_isn + 1
    for chunk in chunks:
        if not chunk:
            continue
        packets.append(
            eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq, ack=server_isn + 1) / Raw(load=chunk)
        )
        seq += len(chunk)

    req_len = sum(len(chunk) for chunk in chunks)
    packets.append(eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=server_isn + 1, ack=client_isn + 1 + req_len))
    response = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    packets.append(
        eth
        / ip_s2c
        / TCP(sport=server_port, dport=client_port, flags="PA", seq=server_isn + 1, ack=client_isn + 1 + req_len)
        / Raw(load=response)
    )
    resp_len = len(response)
    packets.append(
        eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1 + req_len, ack=server_isn + 1 + resp_len)
    )
    packets.append(
        eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="FA", seq=client_isn + 1 + req_len, ack=server_isn + 1 + resp_len)
    )
    packets.append(
        eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="FA", seq=server_isn + 1 + resp_len, ack=client_isn + 2 + req_len)
    )
    packets.append(
        eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 2 + req_len, ack=server_isn + 2 + resp_len)
    )
    return packets


def write_capture(out_path: Path, requests: list[bytes]) -> None:
    packets = []
    for idx, request in enumerate(requests):
        packets.extend(
            build_http_session_packets(
                request,
                client_ip=f"10.70.{idx + 1}.10",
                server_ip="10.80.0.11",
                client_port=25000 + idx,
                server_port=8080,
            )
        )
    wrpcap(str(out_path), packets)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    digest_a = deterministic_hex(32, seed=61)
    digest_b = deterministic_hex(32, seed=62)

    daily = mk_request(
        "POST",
        "/ops/daily",
        {"X-Window": "baseline", "Content-Type": "application/x-www-form-urlencoded"},
        f"report=daily&digest={digest_a}".encode(),
    )
    weekly = mk_request(
        "POST",
        "/ops/weekly",
        {"X-Change-Window": "canary", "Content-Type": "application/x-www-form-urlencoded"},
        b"report=weekly&sites=12",
    )
    export_bulk = mk_request(
        "POST",
        "/ops/export",
        {"X-Export-Class": "bulk", "Content-Type": "application/x-www-form-urlencoded"},
        b"file=ops_rollup.csv&rows=7500",
    )
    clean = mk_request(
        "POST",
        "/ops/weekly",
        {"X-Change-Window": "steady", "Content-Type": "application/x-www-form-urlencoded"},
        b"report=weekly&sites=12",
    )

    write_capture(out_dir / "compare_a.pcap", [daily])
    write_capture(out_dir / "compare_b.pcap", [weekly])
    write_capture(out_dir / "compare_c.pcap", [daily, export_bulk])
    write_capture(out_dir / "compare_d.pcap", [clean, mk_request("POST", "/ops/daily", {"X-Window": "steady", "Content-Type": "application/x-www-form-urlencoded"}, f"report=daily&digest={digest_b}".encode())])


if __name__ == "__main__":
    main()
