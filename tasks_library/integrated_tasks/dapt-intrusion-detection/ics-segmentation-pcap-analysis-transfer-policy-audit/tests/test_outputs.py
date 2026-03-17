import csv
import ipaddress
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path


OUTPUT_FILE = Path("/root/ot_policy_audit.json")
PCAP_FILE = Path("/root/packets.pcap")
INVENTORY_FILE = Path("/root/asset_inventory.csv")
POLICY_FILE = Path("/root/zone_policy.json")


def load_inventory():
    assets = {}
    with INVENTORY_FILE.open(newline="") as f:
        for row in csv.DictReader(f):
            assets[row["ip"]] = {
                "asset_name": row["asset_name"],
                "zone": row["zone"],
            }
    return assets


def load_allowed_rules():
    with POLICY_FILE.open() as f:
        raw = json.load(f)
    return {
        (rule["src_zone"], rule["dst_zone"], rule["protocol"])
        for rule in raw["allowed_rules"]
    }


def iter_pcap_ipv4_packets():
    with PCAP_FILE.open("rb") as f:
        global_header = f.read(24)
        magic = global_header[:4]
        if magic == b"\xd4\xc3\xb2\xa1":
            endian = "<"
        elif magic == b"\xa1\xb2\xc3\xd4":
            endian = ">"
        else:
            raise AssertionError("Unsupported PCAP format")

        while True:
            packet_header = f.read(16)
            if not packet_header:
                break
            if len(packet_header) != 16:
                raise AssertionError("Truncated packet header")
            _, _, incl_len, _ = struct.unpack(endian + "IIII", packet_header)
            data = f.read(incl_len)
            if len(data) != incl_len:
                raise AssertionError("Truncated packet data")
            if len(data) < 34:
                continue
            ether_type = struct.unpack("!H", data[12:14])[0]
            if ether_type != 0x0800:
                continue
            ip_packet = data[14:]
            ihl = (ip_packet[0] & 0x0F) * 4
            if len(ip_packet) < ihl:
                continue
            src_ip = str(ipaddress.ip_address(ip_packet[12:16]))
            dst_ip = str(ipaddress.ip_address(ip_packet[16:20]))
            proto_num = ip_packet[9]
            yield src_ip, dst_ip, proto_num, ip_packet[ihl:]


def is_audited_unicast(ip_text):
    addr = ipaddress.ip_address(ip_text)
    return not (addr.is_multicast or ip_text in {"0.0.0.0", "255.255.255.255"})


def protocol_name(proto_num):
    if proto_num == 6:
        return "TCP"
    if proto_num == 17:
        return "UDP"
    if proto_num == 1:
        return "ICMP"
    return None


def build_reference_output():
    assets = load_inventory()
    allowed_rules = load_allowed_rules()
    edge_packets = Counter()
    edge_ports = defaultdict(set)
    active_assets = set()

    for src_ip, dst_ip, proto_num, payload in iter_pcap_ipv4_packets():
        proto = protocol_name(proto_num)
        if proto is None:
            continue
        if src_ip not in assets or dst_ip not in assets:
            continue
        if not (is_audited_unicast(src_ip) and is_audited_unicast(dst_ip)):
            continue

        edge = (src_ip, dst_ip, proto)
        edge_packets[edge] += 1
        active_assets.add(src_ip)
        active_assets.add(dst_ip)

        if proto in {"TCP", "UDP"} and len(payload) >= 4:
            edge_ports[edge].add(struct.unpack("!H", payload[2:4])[0])

    communication_graph = []
    violations = []
    violating_direction_counts = Counter()
    violating_direction_packet_counts = Counter()
    allowed_edge_count = 0
    allowed_packet_count = 0
    cross_zone_edge_count = 0

    for edge in sorted(edge_packets):
        src_ip, dst_ip, proto = edge
        src_asset = assets[src_ip]
        dst_asset = assets[dst_ip]
        direction = f"{src_asset['zone']}->{dst_asset['zone']}"
        cross_zone = src_asset["zone"] != dst_asset["zone"]
        allowed = (not cross_zone) or (
            src_asset["zone"], dst_asset["zone"], proto
        ) in allowed_rules

        record = {
            "src_ip": src_ip,
            "src_asset": src_asset["asset_name"],
            "src_zone": src_asset["zone"],
            "dst_ip": dst_ip,
            "dst_asset": dst_asset["asset_name"],
            "dst_zone": dst_asset["zone"],
            "protocol": proto,
            "packet_count": edge_packets[edge],
            "dst_ports": sorted(edge_ports.get(edge, set())),
            "cross_zone": cross_zone,
            "direction": direction,
            "status": "allowed" if allowed else "violation",
        }
        communication_graph.append(record)

        if cross_zone:
            cross_zone_edge_count += 1

        if allowed:
            allowed_edge_count += 1
            allowed_packet_count += edge_packets[edge]
        else:
            violating_direction_counts[direction] += 1
            violating_direction_packet_counts[direction] += edge_packets[edge]
            violations.append({**record, "reason": "no matching allow rule"})

    return {
        "summary": {
            "audited_asset_count": len(active_assets),
            "audited_packet_count": sum(edge_packets.values()),
            "directed_edge_count": len(communication_graph),
            "allowed_edge_count": allowed_edge_count,
            "allowed_packet_count": allowed_packet_count,
            "cross_zone_edge_count": cross_zone_edge_count,
            "violating_edge_count": len(violations),
            "violating_packet_count": sum(item["packet_count"] for item in violations),
            "violating_direction_counts": dict(sorted(violating_direction_counts.items())),
            "violating_direction_packet_counts": dict(
                sorted(violating_direction_packet_counts.items())
            ),
        },
        "communication_graph": communication_graph,
        "violations": violations,
    }


def load_output():
    assert OUTPUT_FILE.exists(), "Expected /root/ot_policy_audit.json to exist"
    with OUTPUT_FILE.open() as f:
        return json.load(f)


def test_top_level_shape():
    actual = load_output()
    assert set(actual.keys()) == {"summary", "communication_graph", "violations"}
    assert isinstance(actual["summary"], dict)
    assert isinstance(actual["communication_graph"], list)
    assert isinstance(actual["violations"], list)


def test_summary_matches_reference():
    actual = load_output()
    expected = build_reference_output()
    assert actual["summary"] == expected["summary"]


def test_graph_matches_reference():
    actual = load_output()
    expected = build_reference_output()
    assert actual["communication_graph"] == expected["communication_graph"]


def test_violations_match_reference():
    actual = load_output()
    expected = build_reference_output()
    assert actual["violations"] == expected["violations"]
