import json
from pathlib import Path


OUTPUT = Path("/root/transfer1_shift_constraints.json")

EXPECTED = {
    "board_id": "swap-board-west",
    "swap_requests": [
        {
            "ticket_id": "swap-14",
            "employee": "Kai Jensen",
            "site": "Pier 7",
            "minimum_shift_hours": 4,
            "must_cover": ["2026-04-02 07:00-11:00"],
            "cannot_cover": ["2026-04-03 13:00-17:00"],
            "notes": [],
        },
        {
            "ticket_id": "swap-18",
            "employee": "Marta Silva",
            "site": "Gate C",
            "minimum_shift_hours": 2,
            "must_cover": ["2026-05-12 12:30-16:30", "2026-05-13 09:00-11:00"],
            "cannot_cover": ["2026-05-12 15:00-15:30"],
            "notes": ["Badge pickup required"],
        },
        {
            "ticket_id": "swap-21",
            "employee": "Noah Patel",
            "site": "Warehouse 4",
            "minimum_shift_hours": 3,
            "must_cover": ["2026-06-01 22:00-23:59"],
            "cannot_cover": ["2026-06-02 00:00-02:00"],
            "notes": ["Forklift certified only"],
        },
    ],
    "tool_called": ["constraint_parser"],
}


def test_output_exists():
    assert OUTPUT.exists(), "missing transfer1 output"


def test_output_matches_expected_payload():
    actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert actual == EXPECTED


def test_specific_swap_notes():
    actual = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert actual["swap_requests"][1]["must_cover"][1] == "2026-05-13 09:00-11:00"
    assert actual["swap_requests"][2]["minimum_shift_hours"] == 3
