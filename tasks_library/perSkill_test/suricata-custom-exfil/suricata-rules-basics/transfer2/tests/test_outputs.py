import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap

SID = 2001003
PCAPS_DIR = Path("/root/pcaps")
SURICATA_CONFIG = Path("/root/suricata.yaml")
RULES_FILE = Path("/root/transfer2.rules")


@dataclass(frozen=True)
class HttpCase:
    name: str
    request_bytes: bytes
    should_alert: bool


def _run(cmd: list[str], *, timeout_sec: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)


def _mk_request(method: str, path: str, *, headers: dict[str, str], body: bytes) -> bytes:
    merged_headers = {
        "Host": "cdn.local",
        "Content-Length": str(len(body)),
        "Connection": "close",
        **headers,
    }
    header_lines = b"\r\n".join(f"{key}: {value}".encode() for key, value in merged_headers.items())
    return b"".join([f"{method} {path} HTTP/1.1\r\n".encode(), header_lines, b"\r\n\r\n", body])


def _build_tcp_session_pcap(pcap_path: Path, request: bytes, *, client_port: int) -> None:
    client_ip = "10.30.0.10"
    server_ip = "10.30.0.20"
    server_port = 8080
    client_isn = 23000
    server_isn = 27000

    eth = Ether(src="02:00:00:00:00:61", dst="02:00:00:00:00:62")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    syn = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn)
    synack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    ack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1)

    header_end = request.find(b"\r\n\r\n")
    split1 = max(1, header_end // 2) if header_end != -1 else max(1, len(request) // 3)
    split2 = min(len(request) - 1, header_end + 8) if header_end != -1 else max(split1 + 1, (2 * len(request)) // 3)
    chunks = [request[:split1], request[split1:split2], request[split2:]]

    packets = [syn, synack, ack]
    seq = client_isn + 1
    for chunk in chunks:
        if not chunk:
            continue
        packets.append(eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq, ack=server_isn + 1) / Raw(load=chunk))
        seq += len(chunk)

    req_len = sum(len(chunk) for chunk in chunks)
    packets.append(eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=server_isn + 1, ack=client_isn + 1 + req_len))
    response = b"HTTP/1.1 204 No Content\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    packets.append(
        eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="PA", seq=server_isn + 1, ack=client_isn + 1 + req_len) / Raw(load=response)
    )
    wrpcap(str(pcap_path), packets)


def _parse_eve_alert_sids(eve_path: Path) -> list[int]:
    if not eve_path.exists():
        return []
    sids: list[int] = []
    for line in eve_path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("event_type") != "alert":
            continue
        sid = (obj.get("alert") or {}).get("signature_id")
        if isinstance(sid, int):
            sids.append(sid)
    return sids


def _run_suricata_on_pcap(pcap_path: Path, log_dir: Path) -> list[int]:
    if log_dir.exists():
        shutil.rmtree(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    proc = _run(
        [
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
        ],
        timeout_sec=180,
    )
    assert proc.returncode == 0, proc.stderr
    return _parse_eve_alert_sids(log_dir / "eve.json")


def _cases() -> list[HttpCase]:
    return [
        HttpCase(
            "pos_basic",
            _mk_request(
                "GET",
                "/cdn/diag/pull?node=1a2b3c4d&ticket=123456789012&region=us",
                headers={"x-pull-mode": "stage"},
                body=b"",
            ),
            True,
        ),
        HttpCase(
            "pos_reordered",
            _mk_request(
                "GET",
                "/cdn/diag/pull?region=eu&ticket=987654321098&node=ABCDEF12",
                headers={"X-PULL-MODE": "STAGE"},
                body=b"",
            ),
            True,
        ),
        HttpCase(
            "neg_mode",
            _mk_request(
                "GET",
                "/cdn/diag/pull?node=1a2b3c4d&ticket=123456789012&region=us",
                headers={"X-Pull-Mode": "prod"},
                body=b"",
            ),
            False,
        ),
        HttpCase(
            "neg_ticket",
            _mk_request(
                "GET",
                "/cdn/diag/pull?node=1a2b3c4d&ticket=12345678901&region=us",
                headers={"X-Pull-Mode": "stage"},
                body=b"",
            ),
            False,
        ),
        HttpCase(
            "neg_node",
            _mk_request(
                "GET",
                "/cdn/diag/pull?node=1a2g3c4d&ticket=123456789012",
                headers={"X-Pull-Mode": "stage"},
                body=b"",
            ),
            False,
        ),
        HttpCase(
            "neg_method",
            _mk_request(
                "POST",
                "/cdn/diag/pull?node=1a2b3c4d&ticket=123456789012",
                headers={"X-Pull-Mode": "stage"},
                body=b"unused",
            ),
            False,
        ),
    ]


def test_training_pcaps_exist():
    assert (PCAPS_DIR / "train_pos.pcap").exists()
    assert (PCAPS_DIR / "train_neg.pcap").exists()


def test_training_pcaps(tmp_path: Path):
    assert SID in _run_suricata_on_pcap(PCAPS_DIR / "train_pos.pcap", tmp_path / "train_pos")
    assert SID not in _run_suricata_on_pcap(PCAPS_DIR / "train_neg.pcap", tmp_path / "train_neg")


def test_generated_cases(tmp_path: Path):
    for idx, case in enumerate(_cases(), start=1):
        pcap_path = tmp_path / f"{case.name}.pcap"
        _build_tcp_session_pcap(pcap_path, case.request_bytes, client_port=29000 + idx)
        fired = SID in _run_suricata_on_pcap(pcap_path, tmp_path / f"logs_{case.name}")
        assert fired is case.should_alert, f"{case.name}: expected={case.should_alert} got={fired}"


def test_rule_quality():
    text = RULES_FILE.read_text(errors="replace")
    assert "sid:2001003" in text
    assert "http.method" in text or "http_method" in text
    assert "http.uri" in text or "http_uri" in text
    assert "http.header" in text or "http_header" in text
    assert "pcre" in text
