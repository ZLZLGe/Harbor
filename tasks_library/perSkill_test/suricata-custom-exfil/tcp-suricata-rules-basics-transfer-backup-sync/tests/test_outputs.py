import json
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scapy.all import IP, TCP, Ether, Raw, wrpcap

SID = 1000001
PCAPS_DIR = Path("/root/pcaps")
SURICATA_CONFIG = Path("/root/suricata.yaml")
RULES_FILE = Path("/root/tcp_backup_sync.rules")


@dataclass(frozen=True)
class TcpCase:
    name: str
    payload: bytes
    should_alert: bool
    server_port: int = 4040
    data_from_client: bool = True


def _run(cmd: list[str], *, timeout_sec: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)


def _deterministic_hex(n: int, *, seed: int, uppercase: bool = False) -> str:
    alphabet = "0123456789ABCDEF" if uppercase else "0123456789abcdef"
    r = random.Random(seed)
    return "".join(r.choice(alphabet) for _ in range(n))


def _build_message(lines: list[str], *, sep: bytes) -> bytes:
    return sep.join(line.encode() for line in lines) + sep


def _build_tcp_session_pcap(
    pcap_path: Path,
    *,
    payload: bytes,
    server_port: int,
    client_port: int,
    data_from_client: bool,
) -> None:
    client_ip = "192.0.2.10"
    server_ip = "192.0.2.20"

    client_isn = 51000
    server_isn = 73000

    eth = Ether(src="02:30:00:00:00:01", dst="02:30:00:00:00:02")
    ip_c2s = IP(src=client_ip, dst=server_ip)
    ip_s2c = IP(src=server_ip, dst=client_ip)

    syn = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="S", seq=client_isn)
    synack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="SA", seq=server_isn, ack=client_isn + 1)
    ack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_isn + 1, ack=server_isn + 1)

    cut1 = max(1, len(payload) // 5)
    cut2 = max(cut1 + 1, len(payload) // 2)
    cut3 = max(cut2 + 1, (4 * len(payload)) // 5)
    chunks = [payload[:cut1], payload[cut1:cut2], payload[cut2:cut3], payload[cut3:]]

    seq_client = client_isn + 1
    seq_server = server_isn + 1
    req_packets = []

    if data_from_client:
        for chunk in chunks:
            if not chunk:
                continue
            req_packets.append(
                eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq_client, ack=seq_server) / Raw(load=chunk)
            )
            seq_client += len(chunk)
        client_ack = seq_client
        server_ack = seq_server
    else:
        client_ping = b"HELLO\n"
        ping = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="PA", seq=seq_client, ack=seq_server) / Raw(load=client_ping)
        seq_client += len(client_ping)
        req_packets.append(ping)
        req_packets.append(eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=seq_server, ack=seq_client))

        for chunk in chunks:
            if not chunk:
                continue
            req_packets.append(
                eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="PA", seq=seq_server, ack=seq_client) / Raw(load=chunk)
            )
            seq_server += len(chunk)
        client_ack = seq_client
        server_ack = seq_server

    ack2 = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="A", seq=server_ack, ack=client_ack)
    ack3 = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_ack, ack=server_ack)
    fin1 = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="FA", seq=client_ack, ack=server_ack)
    finack = eth / ip_s2c / TCP(sport=server_port, dport=client_port, flags="FA", seq=server_ack, ack=client_ack + 1)
    lastack = eth / ip_c2s / TCP(sport=client_port, dport=server_port, flags="A", seq=client_ack + 1, ack=server_ack + 1)

    packets = [syn, synack, ack, *req_packets, ack2, ack3, fin1, finack, lastack]
    wrpcap(str(pcap_path), packets)


def _parse_eve_alert_sids(eve_path: Path) -> list[int]:
    sids: list[int] = []
    if not eve_path.exists():
        return sids

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


def _run_tcp_case(case: TcpCase, *, tmp_path: Path, idx: int) -> None:
    pcap_path = tmp_path / f"{case.name}.pcap"
    _build_tcp_session_pcap(
        pcap_path,
        payload=case.payload,
        server_port=case.server_port,
        client_port=31000 + idx,
        data_from_client=case.data_from_client,
    )
    sids = _run_suricata_on_pcap(pcap_path, tmp_path / f"logs_{case.name}")
    has_sid = SID in sids
    assert has_sid == case.should_alert, f"{case.name}: expected_alert={case.should_alert} got_sids={sids}"


def test_output_file_exists() -> None:
    assert RULES_FILE.exists(), f"Missing output file: {RULES_FILE}"


def test_training_positive_alerts(tmp_path: Path) -> None:
    sids = _run_suricata_on_pcap(PCAPS_DIR / "backup_match.pcap", tmp_path / "train_pos")
    assert SID in sids, f"Expected sid {SID} on backup_match.pcap, got {sids}"


def test_training_negative_stays_silent(tmp_path: Path) -> None:
    sids = _run_suricata_on_pcap(PCAPS_DIR / "backup_benign.pcap", tmp_path / "train_neg")
    assert SID not in sids, f"Unexpected sid {SID} on backup_benign.pcap: {sids}"


def test_generated_positive_lf_payload(tmp_path: Path) -> None:
    payload = _build_message(
        [
            "SYNC/3",
            "MODE: MIRROR",
            "DEST: vault",
            "WINDOW: hourly",
            f"PAYLOAD={_deterministic_hex(128, seed=41)}",
            f"TOKEN={_deterministic_hex(32, seed=42)}",
        ],
        sep=b"\n",
    )
    _run_tcp_case(TcpCase("pos_lf_payload", payload, True), tmp_path=tmp_path, idx=1)


def test_generated_positive_crlf_reordered_fields(tmp_path: Path) -> None:
    payload = _build_message(
        [
            "SYNC/3",
            f"TOKEN={_deterministic_hex(32, seed=51, uppercase=True)}",
            "DEST: vault",
            "MODE: MIRROR",
            f"PAYLOAD={_deterministic_hex(192, seed=52)}",
            "JOB: branch-copy",
        ],
        sep=b"\r\n",
    )
    _run_tcp_case(TcpCase("pos_crlf_reordered", payload, True), tmp_path=tmp_path, idx=2)


def test_negative_wrong_port(tmp_path: Path) -> None:
    payload = _build_message(
        [
            "SYNC/3",
            "MODE: MIRROR",
            "DEST: vault",
            f"PAYLOAD={_deterministic_hex(160, seed=61)}",
            f"TOKEN={_deterministic_hex(32, seed=62)}",
        ],
        sep=b"\n",
    )
    _run_tcp_case(TcpCase("neg_wrong_port", payload, False, server_port=5050), tmp_path=tmp_path, idx=3)


def test_negative_wrong_mode(tmp_path: Path) -> None:
    payload = _build_message(
        [
            "SYNC/3",
            "MODE: COPY",
            "DEST: vault",
            f"PAYLOAD={_deterministic_hex(160, seed=71)}",
            f"TOKEN={_deterministic_hex(32, seed=72)}",
        ],
        sep=b"\n",
    )
    _run_tcp_case(TcpCase("neg_wrong_mode", payload, False), tmp_path=tmp_path, idx=4)


def test_negative_short_payload(tmp_path: Path) -> None:
    payload = _build_message(
        [
            "SYNC/3",
            "MODE: MIRROR",
            "DEST: vault",
            f"PAYLOAD={_deterministic_hex(120, seed=81)}",
            f"TOKEN={_deterministic_hex(32, seed=82)}",
        ],
        sep=b"\r\n",
    )
    _run_tcp_case(TcpCase("neg_short_payload", payload, False), tmp_path=tmp_path, idx=5)


def test_negative_token_too_long(tmp_path: Path) -> None:
    payload = _build_message(
        [
            "SYNC/3",
            "MODE: MIRROR",
            "DEST: vault",
            f"PAYLOAD={_deterministic_hex(160, seed=91)}",
            f"TOKEN={_deterministic_hex(33, seed=92)}",
        ],
        sep=b"\n",
    )
    _run_tcp_case(TcpCase("neg_token_too_long", payload, False), tmp_path=tmp_path, idx=6)


def test_negative_token_only_in_note_field(tmp_path: Path) -> None:
    payload = _build_message(
        [
            "SYNC/3",
            "MODE: MIRROR",
            "DEST: vault",
            f"PAYLOAD={_deterministic_hex(160, seed=101)}",
            f"NOTE=TOKEN={_deterministic_hex(32, seed=102)}",
        ],
        sep=b"\n",
    )
    _run_tcp_case(TcpCase("neg_note_field", payload, False), tmp_path=tmp_path, idx=7)


def test_negative_pattern_only_from_server(tmp_path: Path) -> None:
    payload = _build_message(
        [
            "SYNC/3",
            "MODE: MIRROR",
            "DEST: vault",
            f"PAYLOAD={_deterministic_hex(160, seed=111)}",
            f"TOKEN={_deterministic_hex(32, seed=112)}",
        ],
        sep=b"\n",
    )
    _run_tcp_case(TcpCase("neg_from_server", payload, False, data_from_client=False), tmp_path=tmp_path, idx=8)
