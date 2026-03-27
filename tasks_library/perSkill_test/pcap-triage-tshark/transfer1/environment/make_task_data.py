from __future__ import annotations

from pathlib import Path

from scapy.all import Ether, IP, TCP, Raw, wrpcap


def build_request(method: str, uri: str, headers: dict[str, str], body: str) -> bytes:
    body_bytes = body.encode("latin-1")
    all_headers = {
        "Host": "badge.internal",
        "User-Agent": "HarborFixture/1.0",
        "Content-Length": str(len(body_bytes)),
        "Connection": "close",
        **headers,
    }
    header_block = "\r\n".join(f"{name}: {value}" for name, value in all_headers.items()).encode("latin-1")
    return b"".join(
        [
            f"{method} {uri} HTTP/1.1\r\n".encode("latin-1"),
            header_block,
            b"\r\n\r\n",
            body_bytes,
        ]
    )


def build_session(client_ip: str, client_port: int, request_bytes: bytes, start_time: float) -> list[object]:
    server_ip = "10.9.1.5"
    server_port = 8080
    client_seq = 10000 + client_port
    server_seq = 40000 + client_port

    eth = Ether(src="02:00:00:00:00:11", dst="02:00:00:00:00:12")
    c2s = IP(src=client_ip, dst=server_ip)
    s2c = IP(src=server_ip, dst=client_ip)

    packets: list[object] = []
    timeline = start_time

    def stamp(packet: object) -> object:
        nonlocal timeline
        packet.time = timeline
        timeline += 0.01
        return packet

    packets.append(stamp(eth / c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_seq)))
    packets.append(
        stamp(eth / s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_seq, ack=client_seq + 1))
    )
    packets.append(
        stamp(eth / c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_seq + 1, ack=server_seq + 1))
    )

    header_end = request_bytes.find(b"\r\n\r\n")
    split1 = max(1, header_end // 2)
    split2 = min(len(request_bytes) - 1, header_end + 8)
    chunks = [request_bytes[:split1], request_bytes[split1:split2], request_bytes[split2:]]

    seq = client_seq + 1
    for chunk in chunks:
        if not chunk:
            continue
        packets.append(
            stamp(
                eth
                / c2s
                / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq, ack=server_seq + 1)
                / Raw(load=chunk)
            )
        )
        seq += len(chunk)

    request_len = sum(len(chunk) for chunk in chunks)
    packets.append(
        stamp(
            eth
            / s2c
            / TCP(sport=server_port, dport=client_port, flags="A", seq=server_seq + 1, ack=client_seq + 1 + request_len)
        )
    )
    response_bytes = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    packets.append(
        stamp(
            eth
            / s2c
            / TCP(sport=server_port, dport=client_port, flags="PA", seq=server_seq + 1, ack=client_seq + 1 + request_len)
            / Raw(load=response_bytes)
        )
    )
    response_len = len(response_bytes)
    packets.append(
        stamp(
            eth
            / c2s
            / TCP(
                sport=client_port,
                dport=server_port,
                flags="A",
                seq=client_seq + 1 + request_len,
                ack=server_seq + 1 + response_len,
            )
        )
    )
    packets.append(
        stamp(
            eth
            / c2s
            / TCP(
                sport=client_port,
                dport=server_port,
                flags="FA",
                seq=client_seq + 1 + request_len,
                ack=server_seq + 1 + response_len,
            )
        )
    )
    packets.append(
        stamp(
            eth
            / s2c
            / TCP(
                sport=server_port,
                dport=client_port,
                flags="FA",
                seq=server_seq + 1 + response_len,
                ack=client_seq + 2 + request_len,
            )
        )
    )
    packets.append(
        stamp(
            eth
            / c2s
            / TCP(
                sport=client_port,
                dport=server_port,
                flags="A",
                seq=client_seq + 2 + request_len,
                ack=server_seq + 2 + response_len,
            )
        )
    )
    return packets


def main() -> None:
    out_dir = Path("/root/pcaps")
    out_dir.mkdir(parents=True, exist_ok=True)

    requests = [
        ("10.20.0.11", 32001, build_request("POST", "/badge/v1/swipe?site=north-plant&door=A1&badge=B-104", {"Content-Type": "application/x-www-form-urlencoded"}, "result=denied&reason=expired")),
        ("10.20.0.12", 32002, build_request("POST", "/badge/v1/swipe?site=north-plant&door=A2&badge=B-210", {"Content-Type": "application/x-www-form-urlencoded"}, "result=denied&reason=tailgating")),
        ("10.20.0.13", 32003, build_request("POST", "/badge/v1/swipe?site=north-plant&door=A1&badge=B-104", {"Content-Type": "application/x-www-form-urlencoded"}, "result=denied&reason=expired")),
        ("10.20.0.14", 32004, build_request("POST", "/badge/v1/swipe?site=north-plant&door=B4&badge=C-009", {"Content-Type": "application/x-www-form-urlencoded"}, "result=granted&reason=clear")),
        ("10.20.0.15", 32005, build_request("GET", "/badge/v1/swipe?site=north-plant&door=C1&badge=G-777", {}, "")),
    ]

    packets: list[object] = []
    for index, (client_ip, client_port, request_bytes) in enumerate(requests):
        packets.extend(build_session(client_ip, client_port, request_bytes, 1.0 + index * 2.0))

    wrpcap(str(out_dir / "transfer1_badge_access.pcap"), packets)


if __name__ == "__main__":
    main()
