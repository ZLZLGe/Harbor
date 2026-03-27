from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from scapy.all import IP, TCP, Raw, rdpcap


HTTP_METHOD_PREFIXES = (
    b"GET ",
    b"POST ",
    b"PUT ",
    b"DELETE ",
    b"PATCH ",
    b"HEAD ",
    b"OPTIONS ",
)


@dataclass(frozen=True)
class HttpRequest:
    frame_number: int
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    method: str
    uri: str
    path: str
    headers: dict[str, str]
    body_text: str


def read_http_requests(pcap_path: str | Path) -> list[HttpRequest]:
    flows: dict[tuple[str, str, int, int], dict[str, object]] = {}
    packets = rdpcap(str(pcap_path))

    for frame_number, packet in enumerate(packets, start=1):
        if IP not in packet or TCP not in packet or Raw not in packet:
            continue

        payload = bytes(packet[Raw].load)
        if not payload:
            continue

        ip = packet[IP]
        tcp = packet[TCP]
        key = (str(ip.src), str(ip.dst), int(tcp.sport), int(tcp.dport))
        bucket = flows.setdefault(key, {"first_frame": frame_number, "segments": []})
        bucket["first_frame"] = min(int(bucket["first_frame"]), frame_number)
        bucket["segments"].append((int(tcp.seq), frame_number, payload))

    requests: list[HttpRequest] = []
    for (src_ip, dst_ip, src_port, dst_port), bucket in flows.items():
        segments = sorted(bucket["segments"], key=lambda item: (item[0], item[1]))
        merged = bytearray()
        seen_seqs: set[int] = set()
        for seq, _frame_number, payload in segments:
            if seq in seen_seqs:
                continue
            seen_seqs.add(seq)
            merged.extend(payload)

        payload = bytes(merged)
        if not payload.startswith(HTTP_METHOD_PREFIXES):
            continue

        header_bytes, separator, body_bytes = payload.partition(b"\r\n\r\n")
        if not separator:
            continue

        header_lines = header_bytes.decode("latin-1").split("\r\n")
        start_line = header_lines[0].strip().split()
        if len(start_line) < 2:
            continue

        method = start_line[0]
        uri = start_line[1]
        headers: dict[str, str] = {}
        for line in header_lines[1:]:
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()

        requests.append(
            HttpRequest(
                frame_number=int(bucket["first_frame"]),
                src_ip=src_ip,
                src_port=src_port,
                dst_ip=dst_ip,
                dst_port=dst_port,
                method=method,
                uri=uri,
                path=urlsplit(uri).path,
                headers=headers,
                body_text=body_bytes.decode("latin-1"),
            )
        )

    return sorted(requests, key=lambda item: item.frame_number)


def parse_query_params(uri: str) -> dict[str, str]:
    return {key: value for key, value in parse_qsl(urlsplit(uri).query, keep_blank_values=True)}


def parse_form_body(body_text: str) -> dict[str, str]:
    return {key: value for key, value in parse_qsl(body_text, keep_blank_values=True)}


def parse_key_value_lines(body_text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in body_text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result
