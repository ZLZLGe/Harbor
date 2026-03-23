import argparse
import base64
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
    text = text[:n]
    if len(text) >= 8:
        text = text[:4] + "+/" + text[6:]
    return text


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
    client_isn = 12000 + client_port
    server_isn = 22000 + server_port + client_port

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
                client_ip=f"10.30.{idx + 1}.10",
                server_ip="10.40.0.7",
                client_port=23000 + idx,
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

    sig_a = deterministic_hex(64, seed=21)
    blob_a = deterministic_b64(100, seed=31)
    stage_chunk = "ABCD1234ABCD1234ABCD1234ABCD1234"

    exfil = mk_request(
        "POST",
        "/telemetry/v2/report",
        {"X-TLM-Mode": "exfil", "Content-Type": "application/x-www-form-urlencoded"},
        f"blob={blob_a}&sig={sig_a}&src=core".encode(),
    )
    stage = mk_request(
        "POST",
        "/telemetry/v2/stage",
        {"X-TLM-Mode": "stage", "Content-Type": "application/x-www-form-urlencoded"},
        f"job=55443322&chunk={stage_chunk}&site=queue".encode(),
    )
    upload_a = mk_request(
        "POST",
        "/partner/upload",
        {"X-Upload-Class": "finance", "Content-Type": "application/x-www-form-urlencoded"},
        b"file=ledger_2026_03.csv&rows=6400&region=west",
    )
    upload_b = mk_request(
        "POST",
        "/partner/upload",
        {"X-Upload-Class": "finance", "Content-Type": "application/x-www-form-urlencoded"},
        b"region=east&file=recon_2026_03.csv&rows=5100",
    )
    clean = mk_request(
        "POST",
        "/partner/upload",
        {"X-Upload-Class": "general", "Content-Type": "application/x-www-form-urlencoded"},
        b"file=notes.txt&rows=20",
    )

    write_capture(out_dir / "queue_case_1.pcap", [stage])
    write_capture(out_dir / "queue_case_2.pcap", [upload_a, upload_b])
    write_capture(out_dir / "queue_case_3.pcap", [exfil, upload_a])
    write_capture(out_dir / "queue_case_4.pcap", [clean])


if __name__ == "__main__":
    main()
