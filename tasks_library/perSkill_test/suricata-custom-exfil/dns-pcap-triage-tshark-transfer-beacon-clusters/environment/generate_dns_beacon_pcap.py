import argparse
from datetime import datetime, timezone
from pathlib import Path

from scapy.all import DNS, DNSQR, DNSRR, Ether, IP, UDP, wrpcap


RESOLVER_IP = "172.20.0.53"
RESOLVER_MAC = "02:00:00:00:53:53"


def iso_to_epoch(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def add_dns_exchange(
    packets: list,
    *,
    when_iso: str,
    client_ip: str,
    client_mac: str,
    txid: int,
    qname: str,
    qtype: str = "A",
    answer_ip: str = "198.51.100.10",
) -> None:
    when = iso_to_epoch(when_iso)

    request = (
        Ether(src=client_mac, dst=RESOLVER_MAC)
        / IP(src=client_ip, dst=RESOLVER_IP)
        / UDP(sport=40000 + txid, dport=53)
        / DNS(id=txid, rd=1, qd=DNSQR(qname=qname, qtype=qtype))
    )
    request.time = when
    packets.append(request)

    response = (
        Ether(src=RESOLVER_MAC, dst=client_mac)
        / IP(src=RESOLVER_IP, dst=client_ip)
        / UDP(sport=53, dport=40000 + txid)
        / DNS(
            id=txid,
            qr=1,
            aa=0,
            rd=1,
            ra=1,
            qd=DNSQR(qname=qname, qtype=qtype),
            an=DNSRR(rrname=qname, type=qtype, ttl=60, rdata=answer_ip),
        )
    )
    response.time = when + 0.08
    packets.append(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    packets: list = []

    suspicious_one = [
        ("2025-02-11T14:22:10Z", "10.42.0.19", "02:00:00:00:19:01", 101, "d41f2c9a3b7e4c8d91aa55ee0011223344556677.backupsync.net"),
        ("2025-02-11T14:23:10Z", "10.42.0.19", "02:00:00:00:19:01", 102, "f0e1d2c3b4a5968778695a4b3c2d1e0fabcd123456.backupsync.net"),
        ("2025-02-11T14:24:10Z", "10.42.0.19", "02:00:00:00:19:01", 103, "01ab23cd45ef67ab89cd01ef23ab45cd67ef89ab01cd.backupsync.net"),
        ("2025-02-11T14:25:10Z", "10.42.0.19", "02:00:00:00:19:01", 104, "11223344556677889900aabbccddeeff0011223344556677.backupsync.net"),
        ("2025-02-11T14:26:10Z", "10.42.0.19", "02:00:00:00:19:01", 105, "feedfacecafebeef00112233445566778899aabbccddeeff0011.backupsync.net"),
    ]

    suspicious_two = [
        ("2025-02-11T14:31:40Z", "10.42.0.44", "02:00:00:00:44:01", 201, "aa11bb22cc33dd44ee55ff66778899aabbcc.telemetry-cdn.org"),
        ("2025-02-11T14:32:55Z", "10.42.0.44", "02:00:00:00:44:01", 202, "1122aabb3344ccdd5566ee77889900aabbccddeeff.telemetry-cdn.org"),
        ("2025-02-11T14:34:10Z", "10.42.0.44", "02:00:00:00:44:01", 203, "99887766554433221100ffeeddccbbaa001122334455.telemetry-cdn.org"),
        ("2025-02-11T14:35:25Z", "10.42.0.44", "02:00:00:00:44:01", 204, "cafebabedeadbeef00112233445566778899aabbccddeeff.telemetry-cdn.org"),
    ]

    below_threshold = [
        ("2025-02-11T14:40:00Z", "10.42.0.77", "02:00:00:00:77:01", 301, "77889900aabbccddeeff0011223344556677.updates.vendor.net"),
        ("2025-02-11T14:41:00Z", "10.42.0.77", "02:00:00:00:77:01", 302, "889900aabbccddeeff001122334455667788.updates.vendor.net"),
        ("2025-02-11T14:42:00Z", "10.42.0.77", "02:00:00:00:77:01", 303, "9900aabbccddeeff00112233445566778899.updates.vendor.net"),
    ]

    short_queries = [
        ("2025-02-11T14:46:00Z", "10.42.0.88", "02:00:00:00:88:01", 401, "a1.cache-metrics.io"),
        ("2025-02-11T14:47:05Z", "10.42.0.88", "02:00:00:00:88:01", 402, "b2.cache-metrics.io"),
        ("2025-02-11T14:48:10Z", "10.42.0.88", "02:00:00:00:88:01", 403, "c3.cache-metrics.io"),
        ("2025-02-11T14:49:15Z", "10.42.0.88", "02:00:00:00:88:01", 404, "d4.cache-metrics.io"),
        ("2025-02-11T14:50:20Z", "10.42.0.88", "02:00:00:00:88:01", 405, "e5.cache-metrics.io"),
    ]

    irregular_queries = [
        ("2025-02-11T14:55:00Z", "10.42.0.91", "02:00:00:00:91:01", 501, "abcdef0123456789abcdef0123456789abcdef.irregular-node.net"),
        ("2025-02-11T14:55:20Z", "10.42.0.91", "02:00:00:00:91:01", 502, "bcdef0123456789abcdef0123456789abcdef0.irregular-node.net"),
        ("2025-02-11T14:57:30Z", "10.42.0.91", "02:00:00:00:91:01", 503, "cdef0123456789abcdef0123456789abcdef01.irregular-node.net"),
        ("2025-02-11T14:58:40Z", "10.42.0.91", "02:00:00:00:91:01", 504, "def0123456789abcdef0123456789abcdef012.irregular-node.net"),
    ]

    aa_only = [
        ("2025-02-11T15:02:00Z", "10.42.0.60", "02:00:00:00:60:01", 601, "00112233445566778899aabbccddeeff00.backupsync.net"),
        ("2025-02-11T15:03:00Z", "10.42.0.60", "02:00:00:00:60:01", 602, "11223344556677889900aabbccddeeff11.backupsync.net"),
        ("2025-02-11T15:04:00Z", "10.42.0.60", "02:00:00:00:60:01", 603, "223344556677889900aabbccddeeff0011.backupsync.net"),
        ("2025-02-11T15:05:00Z", "10.42.0.60", "02:00:00:00:60:01", 604, "3344556677889900aabbccddeeff001122.backupsync.net"),
    ]

    for when_iso, client_ip, client_mac, txid, qname in suspicious_one + suspicious_two + below_threshold + short_queries + irregular_queries:
        add_dns_exchange(
            packets,
            when_iso=when_iso,
            client_ip=client_ip,
            client_mac=client_mac,
            txid=txid,
            qname=qname,
        )

    for when_iso, client_ip, client_mac, txid, qname in aa_only:
        add_dns_exchange(
            packets,
            when_iso=when_iso,
            client_ip=client_ip,
            client_mac=client_mac,
            txid=txid,
            qname=qname,
            qtype="AAAA",
            answer_ip="2001:db8::60",
        )

    packets.sort(key=lambda packet: float(packet.time))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wrpcap(str(out_path), packets)


if __name__ == "__main__":
    main()
