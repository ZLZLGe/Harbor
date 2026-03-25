from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


INPUT_PATH = Path("/workspace/inputs/irc_mix.pcap")
OUTPUT_PATH = Path("/workspace/outputs/irc_c2_transcript.txt")
EXPECTED_LINES = [
    "2025-02-14T08:11:24Z | controller->bot | !id",
    "2025-02-14T08:11:25Z | bot->controller | uid=0(root) gid=0(root) groups=0(root)",
    "2025-02-14T08:12:02Z | controller->bot | !pwd",
    "2025-02-14T08:12:03Z | bot->controller | /srv/.cache",
    "2025-02-14T08:12:40Z | controller->bot | !exfil plans.txt 96",
    "2025-02-14T08:12:42Z | bot->controller | READY plans.txt chunks=3",
    "2025-02-14T08:13:10Z | controller->bot | !sleep 45",
    "2025-02-14T08:13:11Z | bot->controller | OK sleep=45",
]


def load_lines() -> list[str]:
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"
    return OUTPUT_PATH.read_text().splitlines()


def test_input_exists():
    assert INPUT_PATH.exists(), f"missing input pcap: {INPUT_PATH}"


def test_output_matches_required_transcript_exactly():
    assert load_lines() == EXPECTED_LINES


def test_each_line_uses_required_format():
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \| (controller->bot|bot->controller) \| .+$")
    for line in load_lines():
        assert pattern.fullmatch(line), f"invalid line format: {line}"


def test_timestamps_are_strictly_increasing():
    stamps = []
    for line in load_lines():
        stamp_text = line.split(" | ", 1)[0]
        stamps.append(datetime.strptime(stamp_text, "%Y-%m-%dT%H:%M:%SZ"))
    assert stamps == sorted(stamps)
    assert len(set(stamps)) == len(stamps)


def test_output_does_not_mix_benign_messages():
    content = "\n".join(load_lines())
    assert "morning all" not in content
    assert "green" not in content
    assert "maintenance window" not in content
    assert "patch Tuesday" not in content
