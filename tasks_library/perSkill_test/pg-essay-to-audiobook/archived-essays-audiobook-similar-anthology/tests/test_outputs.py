import re
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup


OUTPUT_MP3 = Path("/root/founder-anthology-audiobook.mp3")
OUTPUT_SCRIPT = Path("/root/founder-anthology-script.txt")
INPUT_DIR = Path("/root/archive_snapshots")
ORDER_FILE = INPUT_DIR / "reading_order.txt"

BODY_SELECTORS = [
    "article[data-main-content='true']",
    "section[data-story='primary']",
    "article.essay-body",
    ".story-body",
]

NOISE_PHRASES = [
    "Issue index",
    "Listen on the go",
    "Become a subscriber",
    "Trending now",
    "Print this issue",
    "Read next",
    "Reply by email to join the discussion.",
    "Comments are closed on archived issues.",
    "Archive Home",
    "Gift a subscription",
    "Related dispatches",
    "Stay in the loop",
    "Subscribe for archive alerts.",
    "Back to the archive index.",
]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def extract_expected_body(html_path: Path) -> str:
    soup = BeautifulSoup(html_path.read_text(), "html.parser")

    container = None
    for selector in BODY_SELECTORS:
        container = soup.select_one(selector)
        if container is not None:
            break

    assert container is not None, f"Could not find expected body content in {html_path}"

    paragraphs = [
        normalize_whitespace(paragraph.get_text(" ", strip=True))
        for paragraph in container.find_all("p")
        if normalize_whitespace(paragraph.get_text(" ", strip=True))
    ]
    assert paragraphs, f"No expected paragraphs extracted from {html_path}"
    return " ".join(paragraphs)


def load_expected_chapters():
    chapters = []
    for raw_line in ORDER_FILE.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue

        number, filename, title = line.split("|", 2)
        chapters.append(
            {
                "number": int(number),
                "title": title,
                "body": extract_expected_body(INPUT_DIR / filename),
            }
        )
    return chapters


def chapter_pattern(number: int, title: str) -> re.Pattern[str]:
    escaped = re.escape(f"Chapter {number}: {title}")
    next_header = rf"(?=Chapter {number + 1}:|\Z)"
    return re.compile(rf"{escaped}\n(.*?){next_header}", re.S)


def get_duration_seconds(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def extract_section(script_text: str, number: int, title: str) -> str:
    match = chapter_pattern(number, title).search(script_text)
    assert match, f"Missing chapter header for Chapter {number}: {title}"
    return match.group(1).strip()


def test_outputs_exist():
    assert OUTPUT_SCRIPT.exists(), f"Missing script output: {OUTPUT_SCRIPT}"
    assert OUTPUT_MP3.exists(), f"Missing MP3 output: {OUTPUT_MP3}"


def test_script_has_two_chapters_in_order():
    script_text = OUTPUT_SCRIPT.read_text()
    headings = re.findall(r"^Chapter \d+: .+$", script_text, flags=re.M)
    expected_headings = [
        f"Chapter {chapter['number']}: {chapter['title']}"
        for chapter in load_expected_chapters()
    ]
    assert headings == expected_headings


def test_script_removes_noise_and_keeps_openings():
    script_text = OUTPUT_SCRIPT.read_text()
    for noise in NOISE_PHRASES:
        assert noise not in script_text, f"Noise leaked into final script: {noise}"

    for chapter in load_expected_chapters():
        section = extract_section(script_text, chapter["number"], chapter["title"])
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        assert lines, f"Chapter {chapter['number']} is empty"
        assert lines[0].startswith("Opening: "), f"Chapter {chapter['number']} is missing the opening line"
        assert chapter["title"] in lines[0], f"Opening line for chapter {chapter['number']} must mention the title"


def test_script_covers_full_body_text():
    script_text = OUTPUT_SCRIPT.read_text()

    for chapter in load_expected_chapters():
        section = extract_section(script_text, chapter["number"], chapter["title"])
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        body_text = " ".join(lines[1:])

        assert normalize(body_text) == normalize(chapter["body"]), (
            f"Chapter {chapter['number']} body text does not match the cleaned essay content"
        )


def test_audio_is_decodable():
    duration_seconds = get_duration_seconds(OUTPUT_MP3)
    assert duration_seconds > 0, "MP3 must contain decodable audio"
