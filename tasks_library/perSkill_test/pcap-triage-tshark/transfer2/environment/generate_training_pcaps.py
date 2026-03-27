from __future__ import annotations

import argparse
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap


REQUESTS = [
  {
    "raw_request": "POST /ops/firmware/update HTTP/1.1\\r\\nHost: deploy.internal\\r\\nX-Deploy-Window: overnight\\r\\nX-Ticket: INC-4401\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\nContent-Length: 53\\r\\nConnection: close\\r\\n\\r\\ndevice_id=pump-17&action=check&reason=&batch=alpha",
    "client_ip": "10.30.0.11",
    "server_ip": "10.30.0.2",
    "client_port": 23001,
    "server_port": 8080,
    "time_offset": 1.0
  },
  {
    "raw_request": "POST /ops/firmware/update HTTP/1.1\\r\\nHost: deploy.internal\\r\\nX-Deploy-Window: overnight\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\nContent-Length: 58\\r\\nConnection: close\\r\\n\\r\\ndevice_id=pump-17&action=rollback&reason=crc_mismatch&batch=alpha",
    "client_ip": "10.30.0.12",
    "server_ip": "10.30.0.2",
    "client_port": 23002,
    "server_port": 8080,
    "time_offset": 2.0
  },
  {
    "raw_request": "POST /ops/firmware/update HTTP/1.1\\r\\nHost: deploy.internal\\r\\nX-Deploy-Window: daytime\\r\\nX-Ticket: INC-4402\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\nContent-Length: 55\\r\\nConnection: close\\r\\n\\r\\ndevice_id=valve-03&action=install&reason=&batch=beta",
    "client_ip": "10.30.0.13",
    "server_ip": "10.30.0.2",
    "client_port": 23003,
    "server_port": 8080,
    "time_offset": 3.0
  },
  {
    "raw_request": "POST /ops/firmware/update HTTP/1.1\\r\\nHost: deploy.internal\\r\\nX-Deploy-Window: maintenance\\r\\nContent-Type: application/x-www-form-urlencoded\\r\\nContent-Length: 62\\r\\nConnection: close\\r\\n\\r\\ndevice_id=fan-22&action=rollback&reason=operator_abort&batch=gamma",
    "client_ip": "10.30.0.14",
    "server_ip": "10.30.0.2",
    "client_port": 23004,
    "server_port": 8080,
    "time_offset": 4.0
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
out_path = out_dir / "device_rollout_review.pcap"
packets = []
for request in REQUESTS:
    packets.extend(build_tcp_session_packets(request))
wrpcap(str(out_path), packets)
duplicate_path = Path("/root/device_rollout_review.pcap")
if duplicate_path != out_path:
    duplicate_path.write_bytes(out_path.read_bytes())
