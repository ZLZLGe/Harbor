import base64
import json
import random
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap

SID = 2305001
PCAPS_DIR = Path("/root/pcaps")
SURICATA_CONFIG = Path("/root/suricata.yaml")
RULES_FILE = Path("/root/smtp_finance_drop.rules")


@dataclass(frozen=True)
class SmtpCase:
    name: str
    recipient: str
    subject: str
    filename: str
    attachment_encoding: str
    attachment_body: str
    boundary: str
    should_alert: bool
    rcpt_command: str = "RCPT TO"


def _run(cmd: list[str], *, timeout_sec: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)


def _deterministic_bytes(length: int, *, seed: int) -> bytes:
    r = random.Random(seed)
    return bytes(r.getrandbits(8) for _ in range(length))


def _wrapped_base64(raw: bytes, *, width: int = 60) -> str:
    text = base64.b64encode(raw).decode()
    return "\r\n".join(text[i : i + width] for i in range(0, len(text), width))


def _quoted_printableish(raw: bytes) -> str:
    return "".join(f"={b:02X}" for b in raw[:48])


def _build_message(case: SmtpCase) -> bytes:
    lines = [
        "From: Vault Bot <vault@corp.example>",
        f"To: {case.recipient}",
        f"Subject: {case.subject}",
        "Date: Mon, 23 Mar 2026 11:00:00 +0000",
        f"Message-ID: <{case.name}@corp.example>",
        "MIME-Version: 1.0",
        f'Content-Type: multipart/mixed; boundary="{case.boundary}"',
        "",
        f"--{case.boundary}",
        'Content-Type: text/plain; charset="utf-8"',
        "Content-Transfer-Encoding: 7bit",
        "",
        "Automated archive dispatch.",
        "",
        f"--{case.boundary}",
        f'Content-Type: application/zip; name="{case.filename}"',
        f"Content-Transfer-Encoding: {case.attachment_encoding}",
        f'Content-Disposition: attachment; filename="{case.filename}"',
        "",
        case.attachment_body,
        f"--{case.boundary}--",
        "",
    ]
    return ("\r\n".join(lines)).encode()


def _split_client_payload(data: bytes) -> list[bytes]:
    marker = data.find(b"Subject:")
    if marker == -1:
        marker = len(data) // 3
    split1 = max(14, marker // 2)
    split2 = max(split1 + 1, marker + 18)
    split3 = max(split2 + 1, len(data) - 64)
    indexes = sorted({split1, split2, split3})
    chunks = []
    start = 0
    for end in indexes:
        chunks.append(data[start:end])
        start = end
    chunks.append(data[start:])
    return [chunk for chunk in chunks if chunk]


def _build_smtp_session_pcap(pcap_path: Path, *, case: SmtpCase, client_port: int) -> None:
    client_ip = "10.66.0.10"
    server_ip = "10.66.0.25"
    server_port = 25

    client_seq = 110000
    server_seq = 210000

    eth = Ether(src="02:00:00:00:40:01", dst="02:00:00:00:40:25")
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
    add_client_payload(f"{case.rcpt_command}:<{case.recipient}>\r\n".encode())
    add_server_payload(b"250 2.1.5 Recipient ok\r\n")
    add_client_payload(b"DATA\r\n")
    add_server_payload(b"354 End data with <CR><LF>.<CR><LF>\r\n")

    for chunk in _split_client_payload(_build_message(case) + b"\r\n.\r\n"):
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

    wrpcap(str(pcap_path), packets)


def _parse_eve_alert_sids(eve_path: Path) -> list[int]:
    if not eve_path.exists():
        return []

    sids: list[int] = []
    for line in eve_path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("event_type") != "alert":
            continue
        alert = obj.get("alert") or {}
        sid = alert.get("signature_id")
        if isinstance(sid, int):
            sids.append(sid)
    return sids


def _run_suricata_on_pcap(pcap_path: Path, log_dir: Path) -> list[int]:
    log_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "suricata",
        "--runmode",
        "single",
        "-c",
        str(SURICATA_CONFIG),
        "-S",
        str(RULES_FILE),
        "-k",
        "none",
        "-r",
        str(pcap_path),
        "-l",
        str(log_dir),
    ]
    proc = _run(cmd, timeout_sec=180)
    assert proc.returncode == 0, f"Suricata failed on {pcap_path.name}:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    return _parse_eve_alert_sids(log_dir / "eve.json")


def _positive_cases() -> list[SmtpCase]:
    return [
        SmtpCase(
            name="pos_exact_match",
            recipient="dropbox@shadow.example",
            subject="Quarterly Archive",
            filename="finance-202603.zip",
            attachment_encoding="base64",
            attachment_body=_wrapped_base64(_deterministic_bytes(180, seed=31)),
            boundary="mail-boundary-a",
            should_alert=True,
        ),
        SmtpCase(
            name="pos_uppercase_rcpt",
            recipient="dropbox@shadow.example",
            subject="Quarterly Archive",
            filename="finance-202512.zip",
            attachment_encoding="base64",
            attachment_body=_wrapped_base64(_deterministic_bytes(192, seed=32)),
            boundary="mail-boundary-b",
            should_alert=True,
            rcpt_command="RcPt To",
        ),
        SmtpCase(
            name="pos_boundary_variation",
            recipient="dropbox@shadow.example",
            subject="Quarterly Archive",
            filename="finance-202401.zip",
            attachment_encoding="base64",
            attachment_body=_wrapped_base64(_deterministic_bytes(168, seed=33)),
            boundary="archive_boundary_202401",
            should_alert=True,
        ),
    ]


def _negative_cases() -> list[SmtpCase]:
    return [
        SmtpCase(
            name="neg_wrong_recipient",
            recipient="opsdrop@shadow.example",
            subject="Quarterly Archive",
            filename="finance-202603.zip",
            attachment_encoding="base64",
            attachment_body=_wrapped_base64(_deterministic_bytes(180, seed=41)),
            boundary="mail-boundary-c",
            should_alert=False,
        ),
        SmtpCase(
            name="neg_wrong_subject",
            recipient="dropbox@shadow.example",
            subject="Quarterly Summary",
            filename="finance-202603.zip",
            attachment_encoding="base64",
            attachment_body=_wrapped_base64(_deterministic_bytes(180, seed=42)),
            boundary="mail-boundary-d",
            should_alert=False,
        ),
        SmtpCase(
            name="neg_wrong_filename",
            recipient="dropbox@shadow.example",
            subject="Quarterly Archive",
            filename="finance-q1-202603.zip",
            attachment_encoding="base64",
            attachment_body=_wrapped_base64(_deterministic_bytes(180, seed=43)),
            boundary="mail-boundary-e",
            should_alert=False,
        ),
        SmtpCase(
            name="neg_not_base64",
            recipient="dropbox@shadow.example",
            subject="Quarterly Archive",
            filename="finance-202603.zip",
            attachment_encoding="quoted-printable",
            attachment_body=_quoted_printableish(_deterministic_bytes(80, seed=44)),
            boundary="mail-boundary-f",
            should_alert=False,
        ),
        SmtpCase(
            name="neg_plaintext_mentions_filename",
            recipient="dropbox@shadow.example",
            subject="Quarterly Archive",
            filename="notes-202603.txt",
            attachment_encoding="base64",
            attachment_body=_wrapped_base64(_deterministic_bytes(180, seed=45))
            + "\r\nThe finance-202603.zip string only appears in a note.",
            boundary="mail-boundary-g",
            should_alert=False,
        ),
    ]


def _run_smtp_case(case: SmtpCase, *, tmp_path: Path, idx: int) -> None:
    pcap_path = tmp_path / f"{case.name}.pcap"
    _build_smtp_session_pcap(pcap_path, case=case, client_port=26000 + idx)
    sids = _run_suricata_on_pcap(pcap_path, tmp_path / f"logs_{case.name}")
    has_sid = SID in sids
    assert has_sid == case.should_alert, f"{case.name}: expected_alert={case.should_alert} got_sids={sids}"


class TestFileLayout:
    def test_training_pcaps_exist(self):
        assert (PCAPS_DIR / "train_pos.pcap").exists()
        assert (PCAPS_DIR / "train_neg.pcap").exists()


class TestTrainingPcaps:
    def test_training_pos_pcap_alerts(self, tmp_path: Path):
        sids = _run_suricata_on_pcap(PCAPS_DIR / "train_pos.pcap", tmp_path / "logs_train_pos")
        assert SID in sids, f"expected sid {SID} in train_pos.pcap, got {sids}"

    def test_training_neg_pcap_does_not_alert(self, tmp_path: Path):
        sids = _run_suricata_on_pcap(PCAPS_DIR / "train_neg.pcap", tmp_path / "logs_train_neg")
        assert SID not in sids, f"unexpected sid {SID} in train_neg.pcap, got {sids}"


class TestGeneratedPcaps:
    def test_generated_pos_1(self, tmp_path: Path):
        _run_smtp_case(_positive_cases()[0], tmp_path=tmp_path, idx=1)

    def test_generated_pos_2(self, tmp_path: Path):
        _run_smtp_case(_positive_cases()[1], tmp_path=tmp_path, idx=2)

    def test_generated_pos_3(self, tmp_path: Path):
        _run_smtp_case(_positive_cases()[2], tmp_path=tmp_path, idx=3)

    def test_generated_neg_1(self, tmp_path: Path):
        _run_smtp_case(_negative_cases()[0], tmp_path=tmp_path, idx=4)

    def test_generated_neg_2(self, tmp_path: Path):
        _run_smtp_case(_negative_cases()[1], tmp_path=tmp_path, idx=5)

    def test_generated_neg_3(self, tmp_path: Path):
        _run_smtp_case(_negative_cases()[2], tmp_path=tmp_path, idx=6)

    def test_generated_neg_4(self, tmp_path: Path):
        _run_smtp_case(_negative_cases()[3], tmp_path=tmp_path, idx=7)

    def test_generated_neg_5(self, tmp_path: Path):
        _run_smtp_case(_negative_cases()[4], tmp_path=tmp_path, idx=8)


class TestRuleQuality:
    def test_rule_is_not_trivially_overbroad(self):
        rule_text = RULES_FILE.read_text(errors="replace")
        lowered = rule_text.lower()
        assert re.search(r"sid\s*:\s*2305001", rule_text), "rule must include sid:2305001"
        assert "dropbox@shadow.example" in lowered
        assert "quarterly archive" in lowered
        assert "base64" in lowered
        assert "finance-" in lowered
