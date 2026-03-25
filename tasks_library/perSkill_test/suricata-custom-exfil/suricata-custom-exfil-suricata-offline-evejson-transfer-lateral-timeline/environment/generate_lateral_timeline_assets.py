import argparse
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap


def assign_times(packets: list, start_time: float, step: float = 0.07) -> None:
    current = start_time
    for packet in packets:
        packet.time = current
        current += step


def split_payload(payload: bytes, cuts: list[int]) -> list[bytes]:
    chunks = []
    start = 0
    for cut in cuts:
        if cut <= start or cut >= len(payload):
            continue
        chunks.append(payload[start:cut])
        start = cut
    chunks.append(payload[start:])
    return [chunk for chunk in chunks if chunk]


def build_tcp_exchange(
    *,
    client_ip: str,
    server_ip: str,
    client_port: int,
    server_port: int,
    request_payload: bytes,
    response_payload: bytes,
) -> list:
    client_isn = 10000 + client_port
    server_isn = 50000 + client_port

    eth = Ether(src="02:00:00:00:70:01", dst="02:00:00:00:70:02")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    packets = [
        eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn),
        eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1),
        eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1),
    ]

    request_chunks = split_payload(
        request_payload,
        [max(1, len(request_payload) // 3), max(2, (2 * len(request_payload)) // 3)],
    )
    seq = client_isn + 1
    for chunk in request_chunks:
        packets.append(
            eth
            / ip_c2s
            / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq, ack=server_isn + 1)
            / Raw(load=chunk)
        )
        seq += len(chunk)

    request_len = sum(len(chunk) for chunk in request_chunks)
    packets.append(
        eth
        / ip_s2c
        / TCP(sport=server_port, dport=client_port, flags="A", seq=server_isn + 1, ack=client_isn + 1 + request_len)
    )

    response_chunks = split_payload(response_payload, [max(1, len(response_payload) // 2)])
    resp_seq = server_isn + 1
    for chunk in response_chunks:
        packets.append(
            eth
            / ip_s2c
            / TCP(sport=server_port, dport=client_port, flags="PA", seq=resp_seq, ack=client_isn + 1 + request_len)
            / Raw(load=chunk)
        )
        resp_seq += len(chunk)

    response_len = sum(len(chunk) for chunk in response_chunks)
    packets.extend(
        [
            eth
            / ip_c2s
            / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1 + request_len, ack=server_isn + 1 + response_len),
            eth
            / ip_c2s
            / TCP(sport=client_port, dport=server_port, flags="FA", seq=client_isn + 1 + request_len, ack=server_isn + 1 + response_len),
            eth
            / ip_s2c
            / TCP(sport=server_port, dport=client_port, flags="FA", seq=server_isn + 1 + response_len, ack=client_isn + 2 + request_len),
            eth
            / ip_c2s
            / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 2 + request_len, ack=server_isn + 2 + response_len),
        ]
    )
    return packets


def smb_payload(*markers: str) -> bytes:
    parts = [b"\xfeSMB", b"command=tree_connect", b"share=\\\\10.77.30.9\\ADMIN$"]
    parts.extend(marker.encode() for marker in markers)
    return b"|".join(parts)


def http_payload(path: str, body: str) -> bytes:
    body_bytes = body.encode()
    headers = [
        f"POST {path} HTTP/1.1",
        "Host: dc2.ops.local",
        "Content-Type: application/soap+xml",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close",
        "",
        "",
    ]
    return "\r\n".join(headers).encode() + body_bytes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcap", required=True)
    args = parser.parse_args()

    output_path = Path(args.pcap)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    events = [
        {
            "start": 1739502855.0,
            "client_ip": "10.77.12.40",
            "server_ip": "10.77.30.9",
            "client_port": 41412,
            "server_port": 3389,
            "request": b"Cookie: mstshash=OPS-HELPDESK|screen=1024x768|color=32",
            "response": b"RDP-ACCEPT",
        },
        {
            "start": 1739502902.0,
            "client_ip": "10.77.20.14",
            "server_ip": "10.77.30.9",
            "client_port": 42011,
            "server_port": 445,
            "request": smb_payload("file=svcctl.dll", "copy=ADMIN$", "svcctl"),
            "response": b"STATUS_SUCCESS",
        },
        {
            "start": 1739502937.0,
            "client_ip": "10.77.20.14",
            "server_ip": "10.77.30.9",
            "client_port": 42012,
            "server_port": 445,
            "request": smb_payload("rpc=svcctl", "CreateServiceW", "RemComSvc"),
            "response": b"SERVICE_CREATED",
        },
        {
            "start": 1739502971.0,
            "client_ip": "10.77.22.17",
            "server_ip": "10.77.31.12",
            "client_port": 42101,
            "server_port": 445,
            "request": b"\xfeSMB|command=query_directory|share=\\\\10.77.31.12\\Users|file=budget.xlsx",
            "response": b"FILE_LIST",
        },
        {
            "start": 1739503032.0,
            "client_ip": "10.77.20.18",
            "server_ip": "10.77.31.22",
            "client_port": 42215,
            "server_port": 445,
            "request": smb_payload("file=svcctl.dll", "copy=ADMIN$", "svcctl"),
            "response": b"STATUS_SUCCESS",
        },
        {
            "start": 1739503085.0,
            "client_ip": "10.77.20.14",
            "server_ip": "10.77.31.22",
            "client_port": 42018,
            "server_port": 445,
            "request": smb_payload("atsvc", "SchRpcRegisterTask", "\\Windows\\Temp\\ops.bat"),
            "response": b"TASK_REGISTERED",
        },
        {
            "start": 1739503181.0,
            "client_ip": "10.77.20.14",
            "server_ip": "10.77.31.22",
            "client_port": 42019,
            "server_port": 445,
            "request": smb_payload("procdump.exe", "lsass", "archive=stage2.zip"),
            "response": b"JOB_DONE",
        },
        {
            "start": 1739503270.0,
            "client_ip": "10.77.40.5",
            "server_ip": "10.77.31.22",
            "client_port": 43001,
            "server_port": 5985,
            "request": http_payload("/wsman", "<s:Envelope><CommandLine>powershell.exe -enc SQBmACgA</CommandLine></s:Envelope>"),
            "response": b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK",
        },
        {
            "start": 1739503353.0,
            "client_ip": "10.77.40.6",
            "server_ip": "10.77.31.22",
            "client_port": 43002,
            "server_port": 5985,
            "request": http_payload("/wsman", "<s:Envelope><CommandLine>powershell.exe -enc UwB0AGEAZwBlADI=</CommandLine></s:Envelope>"),
            "response": b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK",
        },
        {
            "start": 1739503394.0,
            "client_ip": "10.77.20.21",
            "server_ip": "10.77.32.14",
            "client_port": 42031,
            "server_port": 445,
            "request": smb_payload("rpc=svcctl", "CreateServiceW", "RemComSvc"),
            "response": b"SERVICE_CREATED",
        },
    ]

    packets = []
    for event in events:
        session_packets = build_tcp_exchange(
            client_ip=event["client_ip"],
            server_ip=event["server_ip"],
            client_port=event["client_port"],
            server_port=event["server_port"],
            request_payload=event["request"],
            response_payload=event["response"],
        )
        assign_times(session_packets, event["start"])
        packets.extend(session_packets)

    wrpcap(str(output_path), packets)


if __name__ == "__main__":
    main()
