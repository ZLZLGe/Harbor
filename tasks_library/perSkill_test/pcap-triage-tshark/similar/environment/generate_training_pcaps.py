from __future__ import annotations

import argparse
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap


REQUESTS = [
  {
    "raw_request": "POST /telemetry/v2/report HTTP/1.1\\r\\nHost: telemetry.internal\\r\\nX-TLM-Mode: exfil\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\nContent-Length: 175\\r\\nConnection: close\\r\\n\\r\\nblob=ABCD+/efABCD+/efABCD+/efABCD+/efABCD+/efABCD+/efABCD+/efABCD+/efABCD+/efABCD+/efABCD+/efABCD&sig=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef&src=edge-a",
    "client_ip": "10.10.0.11",
    "server_ip": "10.10.0.2",
    "client_port": 21001,
    "server_port": 8080,
    "time_offset": 1.0
  },
  {
    "raw_request": "POST /telemetry/v2/report HTTP/1.1\\r\\nHost: telemetry.internal\\r\\nX-TLM-Mode: normal\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\nContent-Length: 167\\r\\nConnection: close\\r\\n\\r\\nblob=QRST+/uvQRST+/uvQRST+/uvQRST+/uvQRST+/uvQRST+/uvQRST+/uvQRST+/uvQRST+/uvQRST+/uvQRST&sig=fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210&src=edge-b",
    "client_ip": "10.10.0.12",
    "server_ip": "10.10.0.2",
    "client_port": 21002,
    "server_port": 8080,
    "time_offset": 2.0
  },
  {
    "raw_request": "GET /telemetry/v2/report?blob=INLINE&sig=INLINE HTTP/1.1\\r\\nHost: telemetry.internal\\r\\nX-TLM-Mode: exfil\\r\\nContent-Length: 0\\r\\nConnection: close\\r\\n\\r\\n",
    "client_ip": "10.10.0.13",
    "server_ip": "10.10.0.2",
    "client_port": 21003,
    "server_port": 8080,
    "time_offset": 3.0
  },
  {
    "raw_request": "POST /telemetry/v2/report HTTP/1.1\\r\\nHost: telemetry.internal\\r\\nX-TLM-Mode: exfil\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\nContent-Length: 188\\r\\nConnection: close\\r\\n\\r\\nv=2&blob=LMNO+/pqLMNO+/pqLMNO+/pqLMNO+/pqLMNO+/pqLMNO+/pqLMNO+/pqLMNO+/pqLMNO+/pqLMNO+/pqLMNO+/pqLMNO+/pqLMNO+/pq&sig=0011223344556677001122334455667700112233445566770011223344556677&note=batch42",
    "client_ip": "10.10.0.14",
    "server_ip": "10.10.0.2",
    "client_port": 21004,
    "server_port": 8080,
    "time_offset": 4.0
  },
  {
    "raw_request": "POST /telemetry/v2/report HTTP/1.1\\r\\nHost: telemetry.internal\\r\\nX-TLM-Mode: diag\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\nContent-Length: 143\\r\\nConnection: close\\r\\n\\r\\nblob=WXYZ+/abWXYZ+/abWXYZ+/abWXYZ+/abWXYZ+/abWXYZ+/abWXYZ+/abWXYZ&sig=a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4&src=edge-c",
    "client_ip": "10.10.0.15",
    "server_ip": "10.10.0.2",
    "client_port": 21005,
    "server_port": 8080,
    "time_offset": 5.0
  }
]


def build_tcp_session_packets(request: dict):
    request_bytes = request["raw_request"].encode("utf-8")
    client_ip = request["client_ip"]
    server_ip = request["server_ip"]
    client_port = request["client_port"]
    server_port = request["server_port"]
    base_time = float(request["time_offset"])

    client_isn = 10000 + client_port
    server_isn = 20000 + client_port

    eth = Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    syn = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn)
    syn.time = base_time
    synack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    synack.time = base_time + 0.001
    ack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1)
    ack.time = base_time + 0.002

    header_end = request_bytes.find(b"\r\n\r\n")
    if header_end != -1:
        split1 = max(1, header_end // 2)
        split2 = min(len(request_bytes) - 1, header_end + 4 + 12)
        chunks = [request_bytes[:split1], request_bytes[split1:split2], request_bytes[split2:]]
    else:
        split1 = max(1, len(request_bytes) // 3)
        split2 = max(split1 + 1, (2 * len(request_bytes)) // 3)
        chunks = [request_bytes[:split1], request_bytes[split1:split2], request_bytes[split2:]]

    packets = [syn, synack, ack]
    seq = client_isn + 1
    current_time = base_time + 0.003
    for chunk in chunks:
        if not chunk:
            continue
        pkt = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq, ack=server_isn + 1) / Raw(load=chunk)
        pkt.time = current_time
        current_time += 0.001
        packets.append(pkt)
        seq += len(chunk)

    req_len = sum(len(chunk) for chunk in chunks)
    ack2 = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=server_isn + 1, ack=client_isn + 1 + req_len)
    ack2.time = current_time
    current_time += 0.001

    response_bytes = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    resp = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="PA", seq=server_isn + 1, ack=client_isn + 1 + req_len) / Raw(load=response_bytes)
    resp.time = current_time
    current_time += 0.001
    resp_len = len(response_bytes)

    ack3 = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1 + req_len, ack=server_isn + 1 + resp_len)
    ack3.time = current_time
    current_time += 0.001

    fin1 = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="FA", seq=client_isn + 1 + req_len, ack=server_isn + 1 + resp_len)
    fin1.time = current_time
    current_time += 0.001
    finack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="FA", seq=server_isn + 1 + resp_len, ack=client_isn + 2 + req_len)
    finack.time = current_time
    current_time += 0.001
    lastack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 2 + req_len, ack=server_isn + 2 + resp_len)
    lastack.time = current_time

    packets.extend([ack2, resp, ack3, fin1, finack, lastack])
    return packets


ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
args = ap.parse_args()

out_dir = Path(args.out)
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "telemetry_request_audit.pcap"
packets = []
for request in REQUESTS:
    packets.extend(build_tcp_session_packets(request))
wrpcap(str(out_path), packets)
duplicate_path = Path("/root/telemetry_request_audit.pcap")
if duplicate_path != out_path:
    duplicate_path.write_bytes(out_path.read_bytes())
