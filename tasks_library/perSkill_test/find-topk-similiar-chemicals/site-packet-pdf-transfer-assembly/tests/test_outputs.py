from pathlib import Path

from pypdf import PdfReader


OUTPUT_PATH = Path("/root/workspace/site_packet.pdf")

EXPECTED_PAGES = [
    {
        "rotation": 0,
        "phrases": [
            "Packet Section: Gate Briefing",
            "Badge pickup window: 05:45-06:15",
        ],
    },
    {
        "rotation": 0,
        "phrases": [
            "Packet Section: Crew Roster",
            "Lift Team Bravo",
        ],
    },
    {
        "rotation": 90,
        "phrases": [
            "Packet Section: Crane Path Diagram",
            "Keep southern lane clear.",
        ],
    },
    {
        "rotation": 0,
        "phrases": [
            "Packet Section: Chemical Hold Points",
            "Stop-work trigger: vapor alarm",
        ],
    },
    {
        "rotation": 0,
        "phrases": [
            "Packet Section: Permit Summary",
            "Night pour authorization",
        ],
    },
    {
        "rotation": 270,
        "phrases": [
            "Packet Section: Emergency Contacts",
            "Foam trailer dispatch: Channel 4",
        ],
    },
]


def normalized_text(page) -> str:
    return " ".join((page.extract_text() or "").split())


def test_output_exists():
    assert OUTPUT_PATH.exists(), "缺少 /root/workspace/site_packet.pdf"


def test_page_count_matches_assembly():
    reader = PdfReader(str(OUTPUT_PATH))
    assert len(reader.pages) == len(EXPECTED_PAGES), "输出页数不正确"


def test_page_sequence_and_rotation():
    reader = PdfReader(str(OUTPUT_PATH))

    for index, (page, expected) in enumerate(zip(reader.pages, EXPECTED_PAGES), start=1):
        text = normalized_text(page)
        for phrase in expected["phrases"]:
            assert phrase in text, f"第 {index} 页缺少关键文本: {phrase}"

        rotation = (page.rotation or 0) % 360
        assert rotation == expected["rotation"], f"第 {index} 页旋转角度不正确"
