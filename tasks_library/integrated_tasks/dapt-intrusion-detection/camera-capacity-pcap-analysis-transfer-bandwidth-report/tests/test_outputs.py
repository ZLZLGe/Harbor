import csv
import struct
from collections import Counter, defaultdict
from pathlib import Path

REPORT_PATH = Path("/root/camera_capacity_report.tsv")
MAP_PATH = Path("/root/camera_stream_map.csv")
PCAP_PATH = Path("/root/packets.pcap")

FIELDNAMES = [
    "record_type",
    "stream_id",
    "camera_id",
    "uplink_id",
    "camera_ip",
    "destination_ip",
    "protocol",
    "dst_port",
    "packet_count",
    "total_bytes",
    "active_minutes",
    "avg_kbps",
    "peak_minute_index",
    "peak_minute_kbps",
    "burst_ratio",
    "anomalous_burst",
    "summary_metric",
    "summary_value",
]

SUMMARY_ORDER = [
    "total_stream_count",
    "most_congested_uplink",
    "most_congested_peak_minute",
    "most_congested_peak_kbps",
    "burst_stream_count",
    "burst_stream_ids",
]


def read_stream_map():
    with open(MAP_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
    keyed = {}
    for row in rows:
        keyed[
            (
                row["camera_ip"],
                row["destination_ip"],
                row["protocol"].upper(),
                int(row["dst_port"]),
            )
        ] = row
    return rows, keyed


def iter_ipv4_packets(path):
    with open(path, "rb") as f:
        global_header = f.read(24)
        if len(global_header) != 24:
            raise AssertionError("invalid pcap global header")
        magic = global_header[:4]
        if magic == b"\xd4\xc3\xb2\xa1":
            endian = "<"
        elif magic == b"\xa1\xb2\xc3\xd4":
            endian = ">"
        else:
            raise AssertionError("unsupported pcap magic")

        first_timestamp = None

        while True:
            packet_header = f.read(16)
            if not packet_header:
                break
            if len(packet_header) != 16:
                raise AssertionError("truncated pcap packet header")
            ts_sec, ts_usec, incl_len, orig_len = struct.unpack(
                endian + "IIII", packet_header
            )
            payload = f.read(incl_len)
            if len(payload) != incl_len:
                raise AssertionError("truncated pcap payload")

            timestamp = ts_sec + (ts_usec / 1_000_000.0)
            if first_timestamp is None:
                first_timestamp = timestamp

            if len(payload) < 14:
                continue

            ether_type = struct.unpack("!H", payload[12:14])[0]
            offset = 14
            if ether_type == 0x8100 and len(payload) >= 18:
                ether_type = struct.unpack("!H", payload[16:18])[0]
                offset = 18
            if ether_type != 0x0800 or len(payload) < offset + 20:
                continue

            ihl = (payload[offset] & 0x0F) * 4
            if len(payload) < offset + ihl:
                continue

            proto_num = payload[offset + 9]
            if proto_num == 6:
                protocol = "TCP"
            elif proto_num == 17:
                protocol = "UDP"
            else:
                continue

            src_ip = ".".join(str(part) for part in payload[offset + 12 : offset + 16])
            dst_ip = ".".join(str(part) for part in payload[offset + 16 : offset + 20])
            l4_offset = offset + ihl
            if len(payload) < l4_offset + 4:
                continue
            _, dst_port = struct.unpack("!HH", payload[l4_offset : l4_offset + 4])

            minute_index = int((timestamp - first_timestamp) // 60)
            yield src_ip, dst_ip, protocol, dst_port, orig_len, minute_index


def pick_peak(counter):
    if not counter:
        return 0, 0
    return min(counter.items(), key=lambda item: (-item[1], item[0]))


def expected_report():
    stream_rows, stream_lookup = read_stream_map()
    packet_counts = Counter()
    byte_counts = Counter()
    minute_bytes = defaultdict(Counter)
    uplink_minutes = defaultdict(Counter)

    for src_ip, dst_ip, protocol, dst_port, orig_len, minute_index in iter_ipv4_packets(
        PCAP_PATH
    ):
        stream = stream_lookup.get((src_ip, dst_ip, protocol, dst_port))
        if stream is None:
            continue
        stream_id = stream["stream_id"]
        packet_counts[stream_id] += 1
        byte_counts[stream_id] += orig_len
        minute_bytes[stream_id][minute_index] += orig_len
        uplink_minutes[stream["uplink_id"]][minute_index] += orig_len

    expected_streams = []
    burst_stream_ids = []
    for stream in stream_rows:
        stream_id = stream["stream_id"]
        active_counter = minute_bytes[stream_id]
        active_minutes = len(active_counter)
        total_bytes = byte_counts[stream_id]
        packet_count = packet_counts[stream_id]
        peak_minute_index, peak_bytes = pick_peak(active_counter)

        if active_minutes == 0:
            avg_kbps = 0.0
            peak_kbps = 0.0
            burst_ratio = 0.0
        else:
            avg_kbps = total_bytes * 8.0 / (active_minutes * 60.0 * 1000.0)
            peak_kbps = peak_bytes * 8.0 / (60.0 * 1000.0)
            burst_ratio = peak_kbps / avg_kbps if avg_kbps else 0.0

        anomalous_burst = burst_ratio >= 6.0 and peak_kbps >= 5.0
        if anomalous_burst:
            burst_stream_ids.append(stream_id)

        expected_streams.append(
            {
                "record_type": "stream",
                "stream_id": stream_id,
                "camera_id": stream["camera_id"],
                "uplink_id": stream["uplink_id"],
                "camera_ip": stream["camera_ip"],
                "destination_ip": stream["destination_ip"],
                "protocol": stream["protocol"],
                "dst_port": stream["dst_port"],
                "packet_count": str(packet_count),
                "total_bytes": str(total_bytes),
                "active_minutes": str(active_minutes),
                "avg_kbps": f"{avg_kbps:.3f}",
                "peak_minute_index": str(peak_minute_index),
                "peak_minute_kbps": f"{peak_kbps:.3f}",
                "burst_ratio": f"{burst_ratio:.3f}",
                "anomalous_burst": "true" if anomalous_burst else "false",
                "summary_metric": "",
                "summary_value": "",
            }
        )

    uplink_summary = []
    for uplink_id, counter in uplink_minutes.items():
        peak_minute_index, peak_bytes = pick_peak(counter)
        peak_kbps = peak_bytes * 8.0 / (60.0 * 1000.0)
        uplink_summary.append((uplink_id, peak_kbps, peak_minute_index))

    if uplink_summary:
        most_congested_uplink, congested_peak_kbps, congested_peak_minute = min(
            uplink_summary,
            key=lambda item: (-item[1], item[0], item[2]),
        )
    else:
        most_congested_uplink = ""
        congested_peak_kbps = 0.0
        congested_peak_minute = 0

    expected_summaries = [
        {
            "record_type": "summary",
            "stream_id": "",
            "camera_id": "",
            "uplink_id": "",
            "camera_ip": "",
            "destination_ip": "",
            "protocol": "",
            "dst_port": "",
            "packet_count": "",
            "total_bytes": "",
            "active_minutes": "",
            "avg_kbps": "",
            "peak_minute_index": "",
            "peak_minute_kbps": "",
            "burst_ratio": "",
            "anomalous_burst": "",
            "summary_metric": metric,
            "summary_value": value,
        }
        for metric, value in [
            ("total_stream_count", str(len(stream_rows))),
            ("most_congested_uplink", most_congested_uplink),
            ("most_congested_peak_minute", str(congested_peak_minute)),
            ("most_congested_peak_kbps", f"{congested_peak_kbps:.3f}"),
            ("burst_stream_count", str(len(burst_stream_ids))),
            ("burst_stream_ids", ",".join(sorted(burst_stream_ids))),
        ]
    ]

    return expected_streams, expected_summaries


def load_report():
    assert REPORT_PATH.exists(), "report file was not created"
    with open(REPORT_PATH, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        assert reader.fieldnames == FIELDNAMES, "unexpected TSV header"
        return list(reader)


def test_report_structure_and_values():
    rows = load_report()
    expected_streams, expected_summaries = expected_report()

    stream_rows = [row for row in rows if row["record_type"] == "stream"]
    summary_rows = [row for row in rows if row["record_type"] == "summary"]

    assert len(stream_rows) == len(expected_streams)
    assert len(summary_rows) == len(expected_summaries)
    assert stream_rows == expected_streams
    assert [row["summary_metric"] for row in summary_rows] == SUMMARY_ORDER
    assert summary_rows == expected_summaries


def test_summary_consistency():
    rows = load_report()
    stream_rows = [row for row in rows if row["record_type"] == "stream"]
    summary = {
        row["summary_metric"]: row["summary_value"]
        for row in rows
        if row["record_type"] == "summary"
    }

    burst_stream_ids = sorted(
        row["stream_id"] for row in stream_rows if row["anomalous_burst"] == "true"
    )

    assert summary["total_stream_count"] == str(len(stream_rows))
    assert summary["burst_stream_count"] == str(len(burst_stream_ids))
    assert summary["burst_stream_ids"] == ",".join(burst_stream_ids)
