import math
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from scapy.all import IP, TCP, UDP

sys.path.insert(0, "/root/skills/pcap-analysis")

from pcap_utils import flow_metrics, iat_stats, load_packets, producer_consumer_counts, split_by_protocol


RESULT_FILE = Path("/root/smart_building_polling_audit.yaml")
PCAP_FILE = Path("/root/smart_building_devices.pcap")

EXPECTED_TOP_LEVEL_KEYS = [
    "protocol_distribution",
    "global_iat",
    "device_roles",
    "flow_summary",
    "polling_audit",
]

EXPECTED_POLLING_FLOWS = [
    "192.168.50.10:41001->192.168.50.101:47808/udp",
    "192.168.50.10:41002->192.168.50.102:47808/udp",
    "192.168.50.20:56001->192.168.50.110:20000/udp",
]


def flow_key(packet):
    if TCP in packet and IP in packet:
        return (packet[IP].src, packet[IP].dst, packet[TCP].sport, packet[TCP].dport, "TCP")
    if UDP in packet and IP in packet:
        return (packet[IP].src, packet[IP].dst, packet[UDP].sport, packet[UDP].dport, "UDP")
    return None


def reverse_flow(flow):
    src_ip, dst_ip, src_port, dst_port, proto = flow
    return (dst_ip, src_ip, dst_port, src_port, proto)


def render_flow(flow):
    src_ip, dst_ip, src_port, dst_port, proto = flow
    return f"{src_ip}:{src_port}->{dst_ip}:{dst_port}/{proto.lower()}"


def mean(values):
    return sum(values) / len(values) if values else 0.0


def variance(values):
    if not values:
        return 0.0
    avg = mean(values)
    return sum((value - avg) ** 2 for value in values) / len(values)


def load_result():
    assert RESULT_FILE.exists(), "result file not found"
    with open(RESULT_FILE, "r", encoding="utf-8") as handle:
        result = yaml.safe_load(handle)
    assert isinstance(result, dict), "result is not a mapping"
    return result


def compute_expected():
    packets = load_packets(str(PCAP_FILE))
    parts = split_by_protocol(packets)
    timestamps = sorted(float(packet.time) for packet in packets if hasattr(packet, "time"))
    iat = iat_stats(timestamps) or {"iat_mean": 0.0, "iat_variance": 0.0, "iat_cv": 0.0}

    all_nodes = {packet[IP].src for packet in parts["ip"]} | {packet[IP].dst for packet in parts["ip"]}
    roles = producer_consumer_counts(parts["ip"], all_nodes)
    flows = flow_metrics(parts["tcp"], parts["udp"])

    flow_timestamps = defaultdict(list)
    for packet in packets:
        current_flow = flow_key(packet)
        if current_flow is not None:
            flow_timestamps[current_flow].append(float(packet.time))

    polling_flows = []
    beaconing_flows = []
    for flow, seen_timestamps in flow_timestamps.items():
        if len(seen_timestamps) < 5:
            continue

        ordered = sorted(seen_timestamps)
        intervals = [ordered[index + 1] - ordered[index] for index in range(len(ordered) - 1)]
        if not intervals:
            continue

        flow_mean = mean(intervals)
        flow_std = math.sqrt(variance(intervals))
        entry = {
            "flow": render_flow(flow),
            "packet_count": len(ordered),
            "mean_interval_seconds": round(flow_mean, 2),
        }

        if reverse_flow(flow) in flow_timestamps and flow[3] in {47808, 20000} and 8 <= flow_mean <= 20 and flow_std <= 0.2:
            polling_flows.append(entry)

        if reverse_flow(flow) not in flow_timestamps and 15 <= flow_mean <= 90 and flow_std <= 0.2:
            beaconing_flows.append(entry)

    polling_flows.sort(key=lambda item: item["flow"])
    beaconing_flows.sort(key=lambda item: item["flow"])

    obvious_periodic_polling = len(polling_flows) >= 2
    obvious_beaconing = len(beaconing_flows) >= 1
    if obvious_periodic_polling and obvious_beaconing:
        final_assessment = "mixed_periodic_activity"
    elif obvious_periodic_polling:
        final_assessment = "building_polling_present"
    elif obvious_beaconing:
        final_assessment = "beaconing_present"
    else:
        final_assessment = "no_obvious_periodic_activity"

    return {
        "protocol_distribution": {
            "total_packets": len(packets),
            "ip_total": len(parts["ip"]),
            "tcp": len(parts["tcp"]),
            "udp": len(parts["udp"]),
            "icmp": len(parts["icmp"]),
            "arp": len(parts["arp"]),
        },
        "global_iat": {
            "capture_duration_seconds": round(timestamps[-1] - timestamps[0], 2) if timestamps else 0.0,
            "mean_seconds": iat["iat_mean"],
            "variance_seconds": iat["iat_variance"],
            "cv": iat["iat_cv"],
        },
        "device_roles": {
            "num_producers": roles["num_producers"],
            "num_consumers": roles["num_consumers"],
        },
        "flow_summary": {
            "unique_flows": flows["unique_flows"],
            "tcp_flows": flows["tcp_flows"],
            "udp_flows": flows["udp_flows"],
            "bidirectional_flows": flows["bidirectional_flows"],
            "bidirectional_flow_ratio": round(flows["bidirectional_flows"] / flows["unique_flows"], 4)
            if flows["unique_flows"]
            else 0.0,
        },
        "polling_audit": {
            "periodic_polling_flow_count": len(polling_flows),
            "beaconing_flow_count": len(beaconing_flows),
            "polling_flows": polling_flows,
            "beaconing_flows": beaconing_flows,
            "obvious_periodic_polling": obvious_periodic_polling,
            "obvious_beaconing": obvious_beaconing,
            "final_assessment": final_assessment,
        },
    }


def assert_equal(actual, expected, path="root"):
    assert type(actual) is type(expected), f"{path}: expected {type(expected).__name__}, got {type(actual).__name__}"
    if isinstance(expected, dict):
        assert list(actual.keys()) == list(expected.keys()), f"{path}: key order mismatch"
        for key in expected:
            assert_equal(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        assert len(actual) == len(expected), f"{path}: list length mismatch"
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            assert_equal(actual_item, expected_item, f"{path}[{index}]")
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-6), (
            f"{path}: expected {expected}, got {actual}"
        )
    else:
        assert actual == expected, f"{path}: expected {expected}, got {actual}"


def test_result_matches_expected_values():
    result = load_result()
    expected = compute_expected()

    assert list(result.keys()) == EXPECTED_TOP_LEVEL_KEYS, "top-level keys mismatch"
    assert_equal(result, expected)


def test_periodic_polling_present_without_beaconing():
    result = load_result()["polling_audit"]
    assert result["obvious_periodic_polling"] is True, "expected obvious periodic polling"
    assert result["obvious_beaconing"] is False, "expected no obvious beaconing"
    assert result["final_assessment"] == "building_polling_present", "unexpected final assessment"


def test_expected_polling_flows_are_listed_in_order():
    result = load_result()["polling_audit"]
    polling_flows = [entry["flow"] for entry in result["polling_flows"]]
    assert polling_flows == EXPECTED_POLLING_FLOWS, f"unexpected polling flows: {polling_flows}"
    assert result["beaconing_flows"] == [], "beaconing_flows should be empty"
