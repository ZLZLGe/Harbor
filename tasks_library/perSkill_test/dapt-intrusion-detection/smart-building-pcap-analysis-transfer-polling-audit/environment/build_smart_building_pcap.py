#!/usr/bin/env python3

import socket
import struct
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class PacketSpec:
    timestamp: float
    frame: bytes


def checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for index in range(0, len(data), 2):
        total += (data[index] << 8) + data[index + 1]
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def mac_bytes(value: str) -> bytes:
    return bytes(int(part, 16) for part in value.split(":"))


def ip_bytes(value: str) -> bytes:
    return socket.inet_aton(value)


def ethernet_frame(src_mac: str, dst_mac: str, eth_type: int, payload: bytes) -> bytes:
    return mac_bytes(dst_mac) + mac_bytes(src_mac) + struct.pack("!H", eth_type) + payload


def ipv4_packet(src_ip: str, dst_ip: str, proto: int, payload: bytes, ident: int) -> bytes:
    version_ihl = 0x45
    tos = 0
    total_length = 20 + len(payload)
    flags_fragment = 0x4000
    ttl = 64
    header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        tos,
        total_length,
        ident & 0xFFFF,
        flags_fragment,
        ttl,
        proto,
        0,
        ip_bytes(src_ip),
        ip_bytes(dst_ip),
    )
    header_checksum = checksum(header)
    return struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        tos,
        total_length,
        ident & 0xFFFF,
        flags_fragment,
        ttl,
        proto,
        header_checksum,
        ip_bytes(src_ip),
        ip_bytes(dst_ip),
    ) + payload


def tcp_flags(flag_string: str) -> int:
    value = 0
    for flag in flag_string:
        value |= {
            "F": 0x01,
            "S": 0x02,
            "R": 0x04,
            "P": 0x08,
            "A": 0x10,
            "U": 0x20,
        }[flag]
    return value


def tcp_segment(
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq: int,
    ack: int,
    flags: str,
    payload: bytes,
) -> bytes:
    data_offset = 5
    offset_reserved_flags = (data_offset << 12) | tcp_flags(flags)
    window = 8192
    urgent_pointer = 0
    tcp_header = struct.pack(
        "!HHIIHHHH",
        src_port,
        dst_port,
        seq,
        ack,
        offset_reserved_flags,
        window,
        0,
        urgent_pointer,
    )
    pseudo_header = struct.pack(
        "!4s4sBBH",
        ip_bytes(src_ip),
        ip_bytes(dst_ip),
        0,
        6,
        len(tcp_header) + len(payload),
    )
    tcp_checksum = checksum(pseudo_header + tcp_header + payload)
    return struct.pack(
        "!HHIIHHHH",
        src_port,
        dst_port,
        seq,
        ack,
        offset_reserved_flags,
        window,
        tcp_checksum,
        urgent_pointer,
    ) + payload


def udp_segment(src_ip: str, dst_ip: str, src_port: int, dst_port: int, payload: bytes) -> bytes:
    length = 8 + len(payload)
    udp_header = struct.pack("!HHHH", src_port, dst_port, length, 0)
    pseudo_header = struct.pack("!4s4sBBH", ip_bytes(src_ip), ip_bytes(dst_ip), 0, 17, length)
    udp_checksum = checksum(pseudo_header + udp_header + payload)
    return struct.pack("!HHHH", src_port, dst_port, length, udp_checksum) + payload


def icmp_message(message_type: int, code: int, identifier: int, sequence: int, payload: bytes) -> bytes:
    header = struct.pack("!BBHHH", message_type, code, 0, identifier, sequence)
    icmp_checksum = checksum(header + payload)
    return struct.pack("!BBHHH", message_type, code, icmp_checksum, identifier, sequence) + payload


def arp_payload(src_mac: str, src_ip: str, dst_mac: str, dst_ip: str, op: int) -> bytes:
    return struct.pack(
        "!HHBBH6s4s6s4s",
        1,
        0x0800,
        6,
        4,
        op,
        mac_bytes(src_mac),
        ip_bytes(src_ip),
        mac_bytes(dst_mac),
        ip_bytes(dst_ip),
    )


def build_tcp_frame(
    timestamp: float,
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq: int,
    ack: int,
    flags: str,
    payload: bytes = b"",
    ident: int = 0,
) -> PacketSpec:
    tcp_payload = tcp_segment(src_ip, dst_ip, src_port, dst_port, seq, ack, flags, payload)
    ip_payload = ipv4_packet(src_ip, dst_ip, 6, tcp_payload, ident)
    return PacketSpec(timestamp=timestamp, frame=ethernet_frame(src_mac, dst_mac, 0x0800, ip_payload))


def build_udp_frame(
    timestamp: float,
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    payload: bytes,
    ident: int = 0,
) -> PacketSpec:
    udp_payload = udp_segment(src_ip, dst_ip, src_port, dst_port, payload)
    ip_payload = ipv4_packet(src_ip, dst_ip, 17, udp_payload, ident)
    return PacketSpec(timestamp=timestamp, frame=ethernet_frame(src_mac, dst_mac, 0x0800, ip_payload))


def build_icmp_frame(
    timestamp: float,
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    message_type: int,
    identifier: int,
    sequence: int,
    payload: bytes,
    ident: int = 0,
) -> PacketSpec:
    icmp_payload = icmp_message(message_type, 0, identifier, sequence, payload)
    ip_payload = ipv4_packet(src_ip, dst_ip, 1, icmp_payload, ident)
    return PacketSpec(timestamp=timestamp, frame=ethernet_frame(src_mac, dst_mac, 0x0800, ip_payload))


def build_arp_frame(
    timestamp: float,
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    op: int,
) -> PacketSpec:
    payload = arp_payload(src_mac, src_ip, dst_mac, dst_ip, op)
    return PacketSpec(timestamp=timestamp, frame=ethernet_frame(src_mac, dst_mac, 0x0806, payload))


def add_tcp_exchange(
    packets: list[PacketSpec],
    base_time: float,
    client_ip: str,
    server_ip: str,
    client_mac: str,
    server_mac: str,
    src_port: int,
    dst_port: int,
    request_payload: bytes,
    response_payload: bytes,
    seq_seed: int,
    ident_seed: int,
) -> None:
    packets.extend(
        [
            build_tcp_frame(base_time, client_mac, server_mac, client_ip, server_ip, src_port, dst_port, seq_seed, 0, "S", ident=ident_seed),
            build_tcp_frame(
                base_time + 0.01,
                server_mac,
                client_mac,
                server_ip,
                client_ip,
                dst_port,
                src_port,
                seq_seed + 200,
                seq_seed + 1,
                "SA",
                ident=ident_seed + 1,
            ),
            build_tcp_frame(
                base_time + 0.02,
                client_mac,
                server_mac,
                client_ip,
                server_ip,
                src_port,
                dst_port,
                seq_seed + 1,
                seq_seed + 201,
                "A",
                ident=ident_seed + 2,
            ),
            build_tcp_frame(
                base_time + 0.15,
                client_mac,
                server_mac,
                client_ip,
                server_ip,
                src_port,
                dst_port,
                seq_seed + 1,
                seq_seed + 201,
                "PA",
                request_payload,
                ident=ident_seed + 3,
            ),
            build_tcp_frame(
                base_time + 0.28,
                server_mac,
                client_mac,
                server_ip,
                client_ip,
                dst_port,
                src_port,
                seq_seed + 201,
                seq_seed + 1 + len(request_payload),
                "PA",
                response_payload,
                ident=ident_seed + 4,
            ),
            build_tcp_frame(
                base_time + 0.34,
                client_mac,
                server_mac,
                client_ip,
                server_ip,
                src_port,
                dst_port,
                seq_seed + 1 + len(request_payload),
                seq_seed + 201 + len(response_payload),
                "A",
                ident=ident_seed + 5,
            ),
        ]
    )


def write_pcap(path: str, packets: list[PacketSpec]) -> None:
    with open(path, "wb") as handle:
        handle.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 262144, 1))
        for packet in sorted(packets, key=lambda item: item.timestamp):
            seconds = int(packet.timestamp)
            micros = int(round((packet.timestamp - seconds) * 1_000_000))
            payload = packet.frame
            handle.write(struct.pack("<IIII", seconds, micros, len(payload), len(payload)))
            handle.write(payload)


def build_packets() -> list[PacketSpec]:
    hosts = {
        "192.168.50.1": "02:50:00:00:00:01",
        "192.168.50.10": "02:50:00:00:00:10",
        "192.168.50.20": "02:50:00:00:00:20",
        "192.168.50.101": "02:50:00:00:01:01",
        "192.168.50.102": "02:50:00:00:01:02",
        "192.168.50.110": "02:50:00:00:01:10",
        "192.168.50.200": "02:50:00:00:02:00",
        "198.18.0.10": "02:18:00:00:00:10",
    }

    packets: list[PacketSpec] = []

    packets.extend(
        [
            build_arp_frame(0.0, hosts["192.168.50.10"], "ff:ff:ff:ff:ff:ff", "192.168.50.10", "192.168.50.1", 1),
            build_arp_frame(0.02, hosts["192.168.50.1"], hosts["192.168.50.10"], "192.168.50.1", "192.168.50.10", 2),
            build_arp_frame(0.5, hosts["192.168.50.20"], "ff:ff:ff:ff:ff:ff", "192.168.50.20", "192.168.50.1", 1),
            build_arp_frame(0.52, hosts["192.168.50.1"], hosts["192.168.50.20"], "192.168.50.1", "192.168.50.20", 2),
            build_arp_frame(30.0, hosts["192.168.50.101"], "ff:ff:ff:ff:ff:ff", "192.168.50.101", "192.168.50.10", 1),
            build_arp_frame(30.02, hosts["192.168.50.10"], hosts["192.168.50.101"], "192.168.50.10", "192.168.50.101", 2),
        ]
    )

    ident = 100
    for index, base_time in enumerate([1.0, 11.0, 21.0, 31.0, 41.0, 51.0, 61.0]):
        packets.append(
            build_udp_frame(
                base_time,
                hosts["192.168.50.10"],
                hosts["192.168.50.101"],
                "192.168.50.10",
                "192.168.50.101",
                41001,
                47808,
                b"T" * 24,
                ident + index * 2,
            )
        )
        packets.append(
            build_udp_frame(
                base_time + 0.08,
                hosts["192.168.50.101"],
                hosts["192.168.50.10"],
                "192.168.50.101",
                "192.168.50.10",
                47808,
                41001,
                b"R" * 64,
                ident + index * 2 + 1,
            )
        )

    ident = 300
    for index, base_time in enumerate([3.0, 13.0, 23.0, 33.0, 43.0, 53.0, 63.0]):
        packets.append(
            build_udp_frame(
                base_time,
                hosts["192.168.50.10"],
                hosts["192.168.50.102"],
                "192.168.50.10",
                "192.168.50.102",
                41002,
                47808,
                b"H" * 28,
                ident + index * 2,
            )
        )
        packets.append(
            build_udp_frame(
                base_time + 0.09,
                hosts["192.168.50.102"],
                hosts["192.168.50.10"],
                "192.168.50.102",
                "192.168.50.10",
                47808,
                41002,
                b"S" * 72,
                ident + index * 2 + 1,
            )
        )

    ident = 500
    for index, base_time in enumerate([5.0, 20.0, 35.0, 50.0, 65.0]):
        packets.append(
            build_udp_frame(
                base_time,
                hosts["192.168.50.20"],
                hosts["192.168.50.110"],
                "192.168.50.20",
                "192.168.50.110",
                56001,
                20000,
                b"P" * 18,
                ident + index * 2,
            )
        )
        packets.append(
            build_udp_frame(
                base_time + 0.12,
                hosts["192.168.50.110"],
                hosts["192.168.50.20"],
                "192.168.50.110",
                "192.168.50.20",
                20000,
                56001,
                b"Q" * 96,
                ident + index * 2 + 1,
            )
        )

    add_tcp_exchange(
        packets,
        12.5,
        "192.168.50.101",
        "192.168.50.200",
        hosts["192.168.50.101"],
        hosts["192.168.50.200"],
        60101,
        1883,
        b"M" * 90,
        b"A" * 26,
        1000,
        700,
    )
    add_tcp_exchange(
        packets,
        27.5,
        "192.168.50.101",
        "192.168.50.200",
        hosts["192.168.50.101"],
        hosts["192.168.50.200"],
        60102,
        1883,
        b"M" * 100,
        b"A" * 26,
        1400,
        720,
    )
    add_tcp_exchange(
        packets,
        46.5,
        "192.168.50.102",
        "192.168.50.200",
        hosts["192.168.50.102"],
        hosts["192.168.50.200"],
        60103,
        1883,
        b"M" * 94,
        b"A" * 26,
        1800,
        740,
    )
    add_tcp_exchange(
        packets,
        58.4,
        "192.168.50.10",
        "198.18.0.10",
        hosts["192.168.50.10"],
        hosts["198.18.0.10"],
        55010,
        443,
        b"J" * 80,
        b"K" * 140,
        2200,
        760,
    )

    packets.extend(
        [
            build_icmp_frame(
                70.0,
                hosts["192.168.50.1"],
                hosts["192.168.50.20"],
                "192.168.50.1",
                "192.168.50.20",
                8,
                900,
                1,
                b"health-check",
                ident=900,
            ),
            build_icmp_frame(
                70.05,
                hosts["192.168.50.20"],
                hosts["192.168.50.1"],
                "192.168.50.20",
                "192.168.50.1",
                0,
                900,
                1,
                b"health-check",
                ident=901,
            ),
        ]
    )

    return sorted(packets, key=lambda packet: packet.timestamp)


def main(output_path: str) -> None:
    write_pcap(output_path, build_packets())


if __name__ == "__main__":
    main(sys.argv[1])
