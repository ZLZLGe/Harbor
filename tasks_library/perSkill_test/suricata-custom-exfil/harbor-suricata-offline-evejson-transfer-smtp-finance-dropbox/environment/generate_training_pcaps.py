import argparse
import base64
import random
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap


def deterministic_bytes(length: int, seed: int) -> bytes:
    r = random.Random(seed)
    return bytes(r.getrandbits(8) for _ in range(length))


def wrapped_base64(raw: bytes, *, width: int = 60) -> str:
    text = base64.b64encode(raw).decode()
    return "\r\n".join(text[i : i + width] for i in range(0, len(text), width))


def build_message(*, recipient: str, subject: str, filename: str, boundary: str, attachment_encoding: str, attachment_body: str) -> bytes:
    lines = [
        "From: Vault Bot <vault@corp.example>",
        f"To: {recipient}",
        f"Subject: {subject}",
        "Date: Mon, 23 Mar 2026 09:15:00 +0000",
        "Message-ID: <quarterly-archive-202603@corp.example>",
        "MIME-Version: 1.0",
        f'Content-Type: multipart/mixed; boundary="{boundary}"',
        "",
        f"--{boundary}",
        'Content-Type: text/plain; charset="utf-8"',
        "Content-Transfer-Encoding: 7bit",
        "",
        "Please route the requested archive to the mailbox.",
        "",
        f"--{boundary}",
        f'Content-Type: application/zip; name="{filename}"',
        f"Content-Transfer-Encoding: {attachment_encoding}",
        f'Content-Disposition: attachment; filename="{filename}"',
        "",
        attachment_body,
        f"--{boundary}--",
        "",
    ]
    return ("\r\n".join(lines)).encode()


def build_smtp_message(*, recipient: str, subject: str, filename: str, attachment_encoding: str, attachment_body: str, boundary: str) -> bytes:
    return build_message(
        recipient=recipient,
        subject=subject,
        filename=filename,
        boundary=boundary,
        attachment_encoding=attachment_encoding,
        attachment_body=attachment_body,
    )


def split_client_payload(data: bytes) -> list[bytes]:
    if len(data) < 9:
        return [data]
    first = max(12, len(data) // 5)
    second = max(first + 1, len(data) // 2)
    third = max(second + 1, len(data) - 48)
    indexes = sorted({first, second, third})
    chunks = []
    start = 0
    for end in indexes:
        chunks.append(data[start:end])
        start = end
    chunks.append(data[start:])
    return [chunk for chunk in chunks if chunk]


def build_smtp_session_pcap(out_path: Path, *, recipient: str, message: bytes, client_port: int) -> None:
    client_ip = "10.55.0.10"
    server_ip = "10.55.0.25"
    server_port = 25

    client_seq = 70000
    server_seq = 90000

    eth = Ether(src="02:00:00:00:30:01", dst="02:00:00:00:30:25")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    packets = [
        eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_seq),
        eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_seq, ack=client_seq + 1),
        eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_seq + 1, ack=server_seq + 1),
    ]

    client_seq += 1
    server_seq += 1

    def add_server_payload(data: bytes) -> None:
        nonlocal client_seq, server_seq
        packets.append(eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="PA", seq=server_seq, ack=client_seq) / Raw(load=data))
        server_seq += len(data)
        packets.append(eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_seq, ack=server_seq))

    def add_client_payload(data: bytes) -> None:
        nonlocal client_seq, server_seq
        packets.append(eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="PA", seq=client_seq, ack=server_seq) / Raw(load=data))
        client_seq += len(data)
        packets.append(eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=server_seq, ack=client_seq))

    add_server_payload(b"220 mx.shadow.example ESMTP ready\r\n")
    add_client_payload(b"EHLO relay.team.example\r\n")
    add_server_payload(b"250-mx.shadow.example Hello relay.team.example\r\n250 SIZE 10485760\r\n")

    add_client_payload(b"MAIL FROM:<vault@corp.example>\r\n")
    add_server_payload(b"250 2.1.0 Sender ok\r\n")
    add_client_payload(f"RCPT TO:<{recipient}>\r\n".encode())
    add_server_payload(b"250 2.1.5 Recipient ok\r\n")
    add_client_payload(b"DATA\r\n")
    add_server_payload(b"354 End data with <CR><LF>.<CR><LF>\r\n")

    for chunk in split_client_payload(message + b"\r\n.\r\n"):
        add_client_payload(chunk)

    add_server_payload(b"250 2.0.0 Queued\r\n")
    add_client_payload(b"QUIT\r\n")
    add_server_payload(b"221 2.0.0 Bye\r\n")

    packets.extend(
        [
            eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="FA", seq=client_seq, ack=server_seq),
            eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="FA", seq=server_seq, ack=client_seq + 1),
            eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_seq + 1, ack=server_seq + 1),
        ]
    )

    wrpcap(str(out_path), packets)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    pos_attachment = wrapped_base64(deterministic_bytes(180, seed=11))
    neg_attachment = wrapped_base64(deterministic_bytes(180, seed=12))

    pos_message = build_smtp_message(
        recipient="dropbox@shadow.example",
        subject="Quarterly Archive",
        filename="finance-202603.zip",
        attachment_encoding="base64",
        attachment_body=pos_attachment,
        boundary="mail-boundary-202603",
    )
    neg_message = build_smtp_message(
        recipient="dropbox@shadow.example",
        subject="Quarterly Summary",
        filename="finance-202603.zip",
        attachment_encoding="base64",
        attachment_body=neg_attachment,
        boundary="mail-boundary-202603",
    )

    build_smtp_session_pcap(
        out_dir / "train_pos.pcap",
        recipient="dropbox@shadow.example",
        message=pos_message,
        client_port=25251,
    )
    build_smtp_session_pcap(
        out_dir / "train_neg.pcap",
        recipient="dropbox@shadow.example",
        message=neg_message,
        client_port=25252,
    )


if __name__ == "__main__":
    main()
