from html.parser import HTMLParser
from pathlib import Path
import subprocess

OUTPUT_FILE = Path("/root/slide_gallery.html")
VIDEO_FILE = Path("/root/lecture-recording.mp4")
FRAME_DIR = Path("/root/slide_gallery_assets")


def count_video_iframes() -> int:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-skip_frame",
            "nokey",
            "-show_entries",
            "frame=pict_type",
            "-of",
            "csv=p=0",
            str(VIDEO_FILE),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return sum(1 for line in result.stdout.splitlines() if line.strip().startswith("I"))


class GalleryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.titles: list[str] = []
        self.headings: list[str] = []
        self.figures: list[dict[str, object]] = []
        self._in_title = False
        self._in_h1 = False
        self._in_figcaption = False
        self._current_text: list[str] = []
        self._current_figure: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "title":
            self._in_title = True
            self._current_text = []
        elif tag == "h1":
            self._in_h1 = True
            self._current_text = []
        elif tag == "figure":
            classes = (attr_map.get("class") or "").split()
            self._current_figure = {
                "class": classes,
                "data-sequence": attr_map.get("data-sequence"),
                "img": None,
                "figcaption": "",
            }
        elif tag == "img" and self._current_figure is not None:
            self._current_figure["img"] = {
                "src": attr_map.get("src"),
                "alt": attr_map.get("alt"),
            }
        elif tag == "figcaption" and self._current_figure is not None:
            self._in_figcaption = True
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title or self._in_h1 or self._in_figcaption:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self._in_title:
            self.titles.append("".join(self._current_text).strip())
            self._in_title = False
        elif tag == "h1" and self._in_h1:
            self.headings.append("".join(self._current_text).strip())
            self._in_h1 = False
        elif tag == "figcaption" and self._in_figcaption and self._current_figure is not None:
            self._current_figure["figcaption"] = "".join(self._current_text).strip()
            self._in_figcaption = False
        elif tag == "figure" and self._current_figure is not None:
            self.figures.append(self._current_figure)
            self._current_figure = None


class TestSlideGallery:
    def test_extracted_frames_match_video_keyframes(self):
        frames = sorted(FRAME_DIR.glob("slide_*.jpg"))
        expected_count = count_video_iframes()

        assert FRAME_DIR.is_dir()
        assert expected_count > 0
        assert len(frames) == expected_count

        for index, frame_path in enumerate(frames, start=1):
            assert frame_path.name == f"slide_{index:03d}.jpg"

    def test_html_gallery_structure(self):
        assert OUTPUT_FILE.is_file()

        parser = GalleryParser()
        parser.feed(OUTPUT_FILE.read_text(encoding="utf-8"))

        assert parser.titles == ["Lecture Slide Gallery"]
        assert parser.headings == ["Lecture Slide Gallery"]

        frames = sorted(FRAME_DIR.glob("slide_*.jpg"))
        assert len(parser.figures) == len(frames)

        for index, (figure, frame_path) in enumerate(zip(parser.figures, frames), start=1):
            assert "slide-card" in figure["class"]
            assert figure["data-sequence"] == str(index)
            assert figure["img"] == {
                "src": f"slide_gallery_assets/{frame_path.name}",
                "alt": frame_path.name,
            }
            assert figure["figcaption"] == frame_path.name
