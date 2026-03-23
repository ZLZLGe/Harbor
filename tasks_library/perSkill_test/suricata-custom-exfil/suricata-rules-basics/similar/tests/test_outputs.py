import base64
import json
import random
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap

SID = 2001001
PCAPS_DIR = Path("/root/pcaps")
SURICATA_CONFIG = Path("/root/suricata.yaml")
RULES_FILE = Path("/root/similar.rules")


@dataclass(frozen=True)
class HttpCase:
    name: str
    request_bytes: bytes
    should_alert: bool


def _run(cmd: list[str], *, timeout_sec: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)


def _deterministic_hex(n: int, *, seed: int) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def _deterministic_b64(n: int, *, seed: int) -> str:
    rng = random.Random(seed)
    raw = bytes(rng.getrandbits(8) for _ in range(max(1, (n * 3) // 4)))
    text = base64.b64encode(raw).decode().rstrip("=")
    if len(text) < n:
        text += "A" * (n - len(text))
    return text[:n]


def _force_plus_slash(text: str) -> str:
    if len(text) < 8:
        return text + "+/"
    return text[:4] + "+/" + text[6:]


def _mk_request(method: str, path: str, *, headers: dict[str, str], body: bytes) -> bytes:
    merged_headers = {
        "Host": "example.local",
        "Content-Length": str(len(body)),
        "Connection": "close",
        **headers,
    }
    header_lines = b"\r\n".join(f"{key}: {value}".encode() for key, value in merged_headers.items())
    return b"".join([f"{method} {path} HTTP/1.1\r\n".encode(), header_lines, b"\r\n\r\n", body])


def _build_tcp_session_pcap(pcap_path: Path, request: bytes, *, client_port: int) -> None:
    client_ip = "10.10.0.10"
    server_ip = "10.10.0.20"
    server_port = 8080
    client_isn = 7000
    server_isn = 12000

    eth = Ether(src="02:00:00:00:00:11", dst="02:00:00:00:00:22")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    syn = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn)
    synack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    ack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1)

    header_end = request.find(b"\r\n\r\n")
    split1 = max(1, header_end // 2) if header_end != -1 else max(1, len(request) // 3)
    split2 = min(len(request) - 1, header_end + 10) if header_end != -1 else max(split1 + 1, (2 * len(request)) // 3)
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
    response = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
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
    digest1 = _deterministic_hex(40, seed=31)
    digest2 = _deterministic_hex(40, seed=32).upper()
    payload1 = _force_plus_slash(_deterministic_b64(96, seed=41))
    payload2 = _force_plus_slash(_deterministic_b64(88, seed=42))
    payload3 = _force_plus_slash(_deterministic_b64(104, seed=43))
    payload_short = _deterministic_b64(40, seed=44)

    return [
        HttpCase(
            "pos_basic",
            _mk_request(
                "POST",
                "/collect/v1/submit",
                headers={"x-op-mode": "sync", "Content-Type": "application/x-www-form-urlencoded"},
                body=f"v=1&payload={payload1}&site=branch&digest={digest1}&pad=ok".encode(),
            ),
            True,
        ),
        HttpCase(
            "pos_min_length",
            _mk_request(
                "POST",
                "/collect/v1/submit",
                headers={"X-OP-MODE": "SYNC", "Content-Type": "application/x-www-form-urlencoded"},
                body=f"digest={digest2}&payload={payload2}&v=1".encode(),
            ),
            True,
        ),
        HttpCase(
            "neg_mode",
            _mk_request(
                "POST",
                "/collect/v1/submit",
                headers={"X-Op-Mode": "async", "Content-Type": "application/x-www-form-urlencoded"},
                body=f"payload={payload1}&digest={digest1}".encode(),
            ),
            False,
        ),
        HttpCase(
            "neg_short_payload",
            _mk_request(
                "POST",
                "/collect/v1/submit",
                headers={"X-Op-Mode": "sync", "Content-Type": "application/x-www-form-urlencoded"},
                body=f"payload={payload_short}&digest={digest1}".encode(),
            ),
            False,
        ),
        HttpCase(
            "neg_missing_digest",
            _mk_request(
                "POST",
                "/collect/v1/submit",
                headers={"X-Op-Mode": "sync", "Content-Type": "application/x-www-form-urlencoded"},
                body=f"v=1&payload={payload3}&site=branch".encode(),
            ),
            False,
        ),
        HttpCase(
            "neg_query_lookalike",
            _mk_request(
                "GET",
                f"/collect/v1/submit?payload={payload1}&digest={digest1}",
                headers={"X-Op-Mode": "sync"},
                body=b"",
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
        _build_tcp_session_pcap(pcap_path, case.request_bytes, client_port=25000 + idx)
        fired = SID in _run_suricata_on_pcap(pcap_path, tmp_path / f"logs_{case.name}")
        assert fired is case.should_alert, f"{case.name}: expected={case.should_alert} got={fired}"


def test_rule_quality():
    text = RULES_FILE.read_text(errors="replace")
    assert "sid:2001001" in text
    assert "http.method" in text or "http_method" in text
    assert "http.uri" in text or "http_uri" in text
    assert "http.header" in text or "http_header" in text
    assert "http.request_body" in text or "http_client_body" in text or "http_request_body" in text
