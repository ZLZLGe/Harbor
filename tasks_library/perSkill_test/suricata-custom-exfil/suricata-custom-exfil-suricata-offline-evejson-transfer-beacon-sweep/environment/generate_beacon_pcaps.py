import argparse
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap


def mk_request(method: str, path: str, headers: dict[str, str], body: bytes = b"") -> bytes:
    merged_headers = {
        "Host": "beacon.example.net",
        "Content-Length": str(len(body)),
        "Connection": "close",
        **headers,
    }
    header_blob = b"\r\n".join(f"{key}: {value}".encode() for key, value in merged_headers.items())
    return b"".join([f"{method} {path} HTTP/1.1\r\n".encode(), header_blob, b"\r\n\r\n", body])


def build_session_packets(request: bytes, *, client_port: int, client_ip: str, server_ip: str, server_port: int) -> list:
    client_isn = 10000 + client_port
    server_isn = 40000 + client_port

    eth = Ether(src="02:00:00:00:40:01", dst="02:00:00:00:40:02")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    syn = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn)
    synack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    ack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1)

    header_end = request.find(b"\r\n\r\n")
    if header_end == -1:
        split_points = [max(1, len(request) // 2)]
    else:
        split_points = [max(1, header_end // 2), min(len(request) - 1, header_end + 4)]

    chunks = []
    start = 0
    for point in split_points:
        if point <= start or point >= len(request):
            continue
        chunks.append(request[start:point])
        start = point
    chunks.append(request[start:])

    packets = [syn, synack, ack]
    seq = client_isn + 1
    for chunk in chunks:
        if not chunk:
            continue
        packets.append(eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq, ack=server_isn + 1) / Raw(load=chunk))
        seq += len(chunk)

    request_length = sum(len(chunk) for chunk in chunks)
    packets.append(eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=server_isn + 1, ack=client_isn + 1 + request_length))

    response = b"HTTP/1.1 204 No Content\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    packets.append(
        eth
        / ip_s2c
        / TCP(sport=server_port, dport=client_port, flags="PA", seq=server_isn + 1, ack=client_isn + 1 + request_length)
        / Raw(load=response)
    )

    response_length = len(response)
    packets.append(eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1 + request_length, ack=server_isn + 1 + response_length))
    packets.append(eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="FA", seq=client_isn + 1 + request_length, ack=server_isn + 1 + response_length))
    packets.append(eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="FA", seq=server_isn + 1 + response_length, ack=client_isn + 2 + request_length))
    packets.append(eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 2 + request_length, ack=server_isn + 2 + response_length))

    return packets


def write_pcap(path: Path, requests: list[bytes]) -> None:
    packets = []
    for index, request in enumerate(requests):
        packets.extend(
            build_session_packets(
                request,
                client_port=20000 + index,
                client_ip=f"10.50.{index}.10",
                server_ip=f"10.60.{index}.20",
                server_port=8080,
            )
        )
    wrpcap(str(path), packets)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    alpha = [
        mk_request(
            "POST",
            "/cdn/collect",
            {"X-Trace-Mode": "beacon", "Content-Type": "application/x-www-form-urlencoded"},
            b"host=edge-a&pulse=0123abcdeffedcba&slot=01",
        )
    ]
    bravo = [
        mk_request("GET", "/status/poll?node=ab12cd&interval=60", {"User-Agent": "BeaconClient/1.0"}),
        mk_request("GET", "/status/poll?node=ef34gh&interval=60", {"User-Agent": "BeaconClient/1.0"}),
    ]
    charlie = [
        mk_request(
            "POST",
            "/cdn/collect",
            {"X-Trace-Mode": "beacon", "Content-Type": "application/x-www-form-urlencoded"},
            b"pulse=89abcdef01234567&host=edge-c",
        ),
        mk_request(
            "POST",
            "/gateway/checkin",
            {"X-Session": "stage2", "Content-Type": "application/x-www-form-urlencoded"},
            b"id=20240325&op=hb&zone=blue",
        ),
    ]
    delta = [
        mk_request(
            "POST",
            "/cdn/collect",
            {"X-Trace-Mode": "sync", "Content-Type": "application/x-www-form-urlencoded"},
            b"host=edge-d&pulse=0123abcdeffedcba&slot=04",
        ),
        mk_request("GET", "/status/poll?node=ij56kl&interval=30", {"User-Agent": "BeaconClient/1.0"}),
        mk_request(
            "POST",
            "/gateway/checkin",
            {"X-Session": "stage1", "Content-Type": "application/x-www-form-urlencoded"},
            b"id=20240325&op=hb&zone=green",
        ),
    ]
    echo = [
        mk_request(
            "POST",
            "/gateway/checkin",
            {"X-Session": "stage2", "Content-Type": "application/x-www-form-urlencoded"},
            b"id=20240326&op=hb&zone=red",
        ),
        mk_request(
            "POST",
            "/gateway/checkin",
            {"X-Session": "stage2", "Content-Type": "application/x-www-form-urlencoded"},
            b"zone=red&op=hb&id=20240327",
        ),
        mk_request("GET", "/status/poll?node=mn78op&interval=60", {"User-Agent": "BeaconClient/2.1"}),
    ]
    foxtrot = [
        mk_request(
            "POST",
            "/cdn/collect",
            {"X-Trace-Mode": "beacon", "Content-Type": "application/x-www-form-urlencoded"},
            b"host=edge-f&pulse=0123abcdeffedcb&slot=06",
        ),
        mk_request("GET", "/status/poll?node=qr90st&interval=15", {"User-Agent": "BeaconClient/1.0"}),
        mk_request(
            "POST",
            "/gateway/checkin",
            {"X-Session": "stage2", "Content-Type": "application/x-www-form-urlencoded"},
            b"id=alpha999&op=hb&zone=yellow",
        ),
    ]

    samples = {
        "alpha-collector.pcap": alpha,
        "bravo-poll-twice.pcap": bravo,
        "charlie-mixed.pcap": charlie,
        "delta-benign.pcap": delta,
        "echo-stage2-repeat.pcap": echo,
        "foxtrot-clean-noisy.pcap": foxtrot,
    }

    for filename, requests in samples.items():
        write_pcap(out_dir / filename, requests)


if __name__ == "__main__":
    main()
