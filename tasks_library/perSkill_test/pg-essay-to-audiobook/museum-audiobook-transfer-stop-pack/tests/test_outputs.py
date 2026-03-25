import csv
import difflib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile


INPUT_CSV = Path("/root/exhibit_packet/stops.csv")
OUTPUT_ZIP = Path("/root/exhibit-stop-pack.zip")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "before",
    "by",
    "can",
    "could",
    "do",
    "during",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "its",
    "left",
    "not",
    "of",
    "on",
    "only",
    "or",
    "so",
    "than",
    "that",
    "the",
    "their",
    "them",
    "there",
    "these",
    "this",
    "to",
    "today",
    "used",
    "using",
    "visible",
    "was",
    "were",
    "when",
    "with",
    "you",
}


def load_expected_rows():
    with INPUT_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def ffprobe_duration(path: Path) -> float:
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


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def expected_spoken_text(row):
    return f"Stop {row['stop_id'].strip()}. {row['title'].strip()}. {row['narration'].strip()}"


def transcode_for_asr(path: Path, target_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "wav",
            str(target_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def normalize_for_asr(text: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def transcribe_with_pocketsphinx(wav_path: Path) -> str:
    result = subprocess.run(
        [
            "pocketsphinx_continuous",
            "-infile",
            str(wav_path),
            "-logfn",
            "/dev/null",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return normalize_spaces(result.stdout)


def content_tokens(tokens: list[str]) -> list[str]:
    return [token for token in tokens if len(token) >= 4 and token not in STOPWORDS]


def longest_common_subsequence_ratio(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 1.0
    matcher = difflib.SequenceMatcher(a=expected, b=actual, autojunk=False)
    return sum(block.size for block in matcher.get_matching_blocks()) / len(expected)


def similarity_metrics(transcript: str, spoken_text: str) -> dict[str, float]:
    expected_tokens = normalize_for_asr(spoken_text)
    transcript_tokens = normalize_for_asr(transcript)

    expected_content = content_tokens(expected_tokens)
    transcript_content = content_tokens(transcript_tokens)

    return {
        "content_lcs_ratio": longest_common_subsequence_ratio(expected_content, transcript_content),
        "full_lcs_ratio": longest_common_subsequence_ratio(expected_tokens, transcript_tokens),
        "combined_score": longest_common_subsequence_ratio(expected_content, transcript_content)
        + longest_common_subsequence_ratio(expected_tokens, transcript_tokens),
    }


def transcribe_audio_for_similarity(audio_path: Path) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = Path(tmpdir) / "audio.wav"
        transcode_for_asr(audio_path, wav_path)
        return transcribe_with_pocketsphinx(wav_path)


def extract_archive():
    temp_dir = tempfile.TemporaryDirectory()
    with ZipFile(OUTPUT_ZIP) as archive:
        archive.extractall(temp_dir.name)
    return temp_dir, Path(temp_dir.name)


def test_output_zip_exists():
    assert OUTPUT_ZIP.exists(), f"Missing output: {OUTPUT_ZIP}"
    assert OUTPUT_ZIP.stat().st_size > 0, "Zip output is empty"


def test_zip_has_exact_required_files():
    expected_rows = load_expected_rows()
    expected_names = ["manifest.json"] + [f"{row['stop_id'].strip()}.mp3" for row in expected_rows]

    with ZipFile(OUTPUT_ZIP) as archive:
        names = archive.namelist()

    assert set(names) == set(expected_names), f"Zip contents do not match the required root layout: {names}"
    assert all("/" not in name.rstrip("/") for name in names), f"Zip contents must be stored at the archive root: {names}"


def test_manifest_matches_csv_exactly():
    expected_rows = load_expected_rows()
    temp_dir, extracted_dir = extract_archive()
    try:
        manifest = json.loads((extracted_dir / "manifest.json").read_text(encoding="utf-8"))
    finally:
        temp_dir.cleanup()

    assert isinstance(manifest, list), "manifest.json must be a JSON array"
    assert len(manifest) == len(expected_rows)

    for item, row in zip(manifest, expected_rows):
        assert set(item.keys()) == {
            "stop_id",
            "title",
            "audio_file",
            "duration_hint_seconds",
            "spoken_text",
        }
        assert item["stop_id"] == row["stop_id"].strip()
        assert item["title"] == row["title"].strip()
        assert item["audio_file"] == f"{row['stop_id'].strip()}.mp3"
        assert item["duration_hint_seconds"] == int(row["duration_hint_seconds"])
        assert normalize_spaces(item["spoken_text"]) == normalize_spaces(expected_spoken_text(row))


def test_each_mp3_is_playable_and_matches_duration_contract():
    expected_rows = load_expected_rows()
    temp_dir, extracted_dir = extract_archive()
    try:
        manifest = json.loads((extracted_dir / "manifest.json").read_text(encoding="utf-8"))

        for item, row in zip(manifest, expected_rows):
            audio_path = extracted_dir / item["audio_file"]
            assert audio_path.exists(), f"Missing audio file {item['audio_file']}"

            duration_seconds = ffprobe_duration(audio_path)
            assert duration_seconds > 3.0, f"{audio_path.name} is too short to be a usable stop"

            hint = int(row["duration_hint_seconds"])
            assert abs(duration_seconds - hint) <= 12.0, (
                f"{audio_path.name} duration {duration_seconds:.1f}s is not within 12 seconds of hint {hint}s"
            )

            word_count = len(re.findall(r"\b[\w'-]+\b", item["spoken_text"]))
            min_duration = word_count / 260 * 60
            max_duration = word_count / 100 * 60

            assert duration_seconds >= min_duration, (
                f"{audio_path.name} is too short for a full reading of its spoken_text"
            )
            assert duration_seconds <= max_duration, (
                f"{audio_path.name} is unexpectedly long for its spoken_text"
            )
            assert audio_path.stat().st_size > 0, f"{audio_path.name} is empty"
    finally:
        temp_dir.cleanup()


def test_each_mp3_speaks_its_expected_script():
    expected_rows = load_expected_rows()
    expected_scripts = {row["stop_id"].strip(): expected_spoken_text(row) for row in expected_rows}
    temp_dir, extracted_dir = extract_archive()
    try:
        manifest = json.loads((extracted_dir / "manifest.json").read_text(encoding="utf-8"))

        for item, row in zip(manifest, expected_rows):
            audio_path = extracted_dir / item["audio_file"]
            transcript = transcribe_audio_for_similarity(audio_path)
            scored_matches = []
            for stop_id, spoken_text in expected_scripts.items():
                metrics = similarity_metrics(transcript, spoken_text)
                scored_matches.append((metrics["combined_score"], stop_id, metrics))

            scored_matches.sort(reverse=True)
            best_score, best_stop_id, best_metrics = scored_matches[0]
            runner_up_score = scored_matches[1][0] if len(scored_matches) > 1 else 0.0

            assert best_stop_id == row["stop_id"].strip(), (
                f"{audio_path.name} transcription matched stop {best_stop_id} more closely than "
                f"{row['stop_id'].strip()}; transcript={transcript!r}; scores={scored_matches}"
            )
            assert best_metrics["full_lcs_ratio"] >= 0.18, (
                f"{audio_path.name} transcript is too dissimilar from its expected script: "
                f"{best_metrics['full_lcs_ratio']:.2f}; transcript={transcript!r}"
            )
            assert best_metrics["content_lcs_ratio"] >= 0.10, (
                f"{audio_path.name} transcription did not retain enough script content: "
                f"{best_metrics['content_lcs_ratio']:.2f}; transcript={transcript!r}"
            )
            assert best_score >= 0.30, (
                f"{audio_path.name} did not produce a strong enough transcript match to any expected script: "
                f"{best_score:.2f}; transcript={transcript!r}"
            )
            assert best_score - runner_up_score >= 0.08, (
                f"{audio_path.name} transcript was too ambiguous between scripts: "
                f"best={best_score:.2f}, runner_up={runner_up_score:.2f}; transcript={transcript!r}"
            )
    finally:
        temp_dir.cleanup()
