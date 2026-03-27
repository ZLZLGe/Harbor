from __future__ import annotations

from pathlib import Path

from scapy.all import Ether, IP, TCP, Raw, wrpcap


def build_request(method: str, uri: str, headers: dict[str, str], body: str) -> bytes:
    body_bytes = body.encode("latin-1")
    all_headers = {
        "Host": "telemetry.internal",
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
    server_ip = "10.9.0.5"
    server_port = 8080
    client_seq = 10000 + client_port
    server_seq = 40000 + client_port

    eth = Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02")
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
    if header_end != -1:
        split1 = max(1, header_end // 2)
        split2 = min(len(request_bytes) - 1, header_end + 8)
        chunks = [request_bytes[:split1], request_bytes[split1:split2], request_bytes[split2:]]
    else:
        split1 = max(1, len(request_bytes) // 3)
        split2 = max(split1 + 1, (2 * len(request_bytes)) // 3)
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
        {
            "client_ip": "10.8.0.11",
            "client_port": 31001,
            "request": build_request(
                "POST",
                "/telemetry/v2/report",
                {
                    "X-TLM-Mode": " exfil ",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                "v=2&blob=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA&src=telemetry&sig=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef&pad=000",
            ),
        },
        {
            "client_ip": "10.8.0.12",
            "client_port": 31002,
            "request": build_request(
                "POST",
                "/telemetry/v2/report",
                {
                    "x-tlm-mode": "normal",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                "v=2&blob=BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB&src=telemetry&sig=abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            ),
        },
        {
            "client_ip": "10.8.0.13",
            "client_port": 31003,
            "request": build_request(
                "POST",
                "/telemetry/v2/report",
                {
                    "X-TLM-Mode": "EXFIL",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                "v=2&blob=CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC&sig=ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            ),
        },
        {
            "client_ip": "10.8.0.14",
            "client_port": 31004,
            "request": build_request(
                "GET",
                "/telemetry/v2/report",
                {
                    "X-TLM-Mode": "exfil",
                },
                "",
            ),
        },
        {
            "client_ip": "10.8.0.15",
            "client_port": 31005,
            "request": build_request(
                "POST",
                "/telemetry/v2/check",
                {
                    "X-TLM-Mode": "exfil",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                "blob=DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD&sig=9999999999999999999999999999999999999999999999999999999999999999",
            ),
        },
    ]

    packets: list[object] = []
    for index, item in enumerate(requests):
        packets.extend(build_session(item["client_ip"], item["client_port"], item["request"], 1.0 + index * 2.0))

    wrpcap(str(out_dir / "similar_telemetry.pcap"), packets)


if __name__ == "__main__":
    main()
