import argparse
import base64
import json
import random
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap


def deterministic_hex(n: int, seed: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def deterministic_b64(n: int, seed: int) -> str:
    rng = random.Random(seed)
    raw = bytes(rng.getrandbits(8) for _ in range(max(1, (n * 3) // 4)))
    text = base64.b64encode(raw).decode().rstrip("=")
    if len(text) < n:
        text += "A" * (n - len(text))
    return text[:n]


def force_plus_slash(text: str) -> str:
    if len(text) < 8:
        return text + "+/"
    return text[:4] + "+/" + text[6:]


def mk_request(method: str, path: str, headers: dict[str, str], body: bytes) -> bytes:
    merged_headers = {
        "Host": "api.local",
        "Content-Length": str(len(body)),
        "Connection": "close",
        **headers,
    }
    header_lines = b"\r\n".join(f"{key}: {value}".encode() for key, value in merged_headers.items())
    return b"".join([f"{method} {path} HTTP/1.1\r\n".encode(), header_lines, b"\r\n\r\n", body])


def build_tcp_session_pcap(out_path: Path, request: bytes, *, client_port: int) -> None:
    client_ip = "10.20.0.10"
    server_ip = "10.20.0.20"
    server_port = 8080
    client_isn = 13000
    server_isn = 17000

    eth = Ether(src="02:00:00:00:00:31", dst="02:00:00:00:00:32")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    syn = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn)
    synack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    ack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1)

    header_end = request.find(b"\r\n\r\n")
    split1 = max(1, header_end // 2) if header_end != -1 else max(1, len(request) // 3)
    split2 = min(len(request) - 1, header_end + 12) if header_end != -1 else max(split1 + 1, (2 * len(request)) // 3)
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
    response = b"HTTP/1.1 202 Accepted\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
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

    payload = force_plus_slash(deterministic_b64(104, seed=51))
    sha = deterministic_hex(64, seed=61)

    pos_body = json.dumps({"batch": "nightly", "payload": payload, "sha256": sha, "site": "alpha"}, separators=(",", ":")).encode()
    neg_body = json.dumps({"batch": "nightly", "payload": payload, "sha256": sha, "site": "alpha"}, separators=(",", ":")).encode()

    build_tcp_session_pcap(
        out_dir / "train_pos.pcap",
        mk_request(
            "PUT",
            "/snapshot/api/v1/upload",
            {"x-archive-intent": "mirror", "Content-Type": "application/json"},
            pos_body,
        ),
        client_port=26001,
    )
    build_tcp_session_pcap(
        out_dir / "train_neg.pcap",
        mk_request(
            "PUT",
            "/snapshot/api/v1/upload",
            {"x-archive-intent": "delta", "Content-Type": "application/json"},
            neg_body,
        ),
        client_port=26002,
    )


if __name__ == "__main__":
    main()
