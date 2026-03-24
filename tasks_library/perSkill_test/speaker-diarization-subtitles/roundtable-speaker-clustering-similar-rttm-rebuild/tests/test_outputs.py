import argparse
import json
from pathlib import Path

from pyannote.core import Annotation, Segment
from pyannote.metrics.diarization import DiarizationErrorRate, JaccardErrorRate

OUTPUT_RTTM = Path("/root/panel_diarization.rttm")
REFERENCE_RTTM = Path("/tests/reference.rttm")
INPUT_JSON = Path("/root/panel_segments.json")
DER_THRESHOLD = 0.02
JER_THRESHOLD = 0.02


def parse_rttm(path: Path):
    turns = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 10:
            raise ValueError(f"line {line_number}: expected 10 fields, got {len(parts)}")
        if parts[0] != "SPEAKER":
            raise ValueError(f"line {line_number}: only SPEAKER entries are allowed")
        start = float(parts[3])
        duration = float(parts[4])
        turns.append(
            {
                "file_id": parts[1],
                "channel": parts[2],
                "start": start,
                "duration": duration,
                "end": start + duration,
                "speaker": parts[7],
            }
        )
    return turns


def read_input_metadata():
    return json.loads(INPUT_JSON.read_text(encoding="utf-8"))


def to_annotation(turns):
    annotation = Annotation()
    for turn in turns:
        annotation[Segment(turn["start"], turn["end"])] = turn["speaker"]
    return annotation


def compute_metrics():
    reference_turns = parse_rttm(REFERENCE_RTTM)
    output_turns = parse_rttm(OUTPUT_RTTM)
    der_metric = DiarizationErrorRate(collar=0.0)
    jer_metric = JaccardErrorRate()
    reference = to_annotation(reference_turns)
    output = to_annotation(output_turns)
    return {
        "der": float(der_metric(reference, output)),
        "jer": float(jer_metric(reference, output)),
        "num_turns": len(output_turns),
        "num_speakers": len({turn["speaker"] for turn in output_turns}),
    }


def test_output_exists():
    assert OUTPUT_RTTM.exists(), "missing /root/panel_diarization.rttm"


def test_rttm_format():
    metadata = read_input_metadata()
    turns = parse_rttm(OUTPUT_RTTM)
    assert turns, "RTTM must contain at least one turn"
    last_end = -1.0
    for turn in turns:
        assert turn["file_id"] == metadata["session_id"]
        assert turn["channel"] == "1"
        assert turn["duration"] > 0
        assert turn["start"] >= 0
        assert turn["start"] >= last_end
        last_end = turn["end"]


def test_speaker_count_and_merge():
    metadata = read_input_metadata()
    turns = parse_rttm(OUTPUT_RTTM)
    assert len({turn["speaker"] for turn in turns}) == 4
    assert len(turns) == 11
    merge_gap = float(metadata["merge_gap_sec"])
    for previous, current in zip(turns, turns[1:]):
        gap = current["start"] - previous["end"]
        assert not (
            previous["speaker"] == current["speaker"] and gap <= merge_gap + 1e-9
        ), "adjacent same-speaker turns within merge_gap_sec must be merged"


def test_matches_reference():
    metrics = compute_metrics()
    assert metrics["der"] <= DER_THRESHOLD, metrics
    assert metrics["jer"] <= JER_THRESHOLD, metrics


def write_score(path: Path):
    if OUTPUT_RTTM.exists():
        metrics = compute_metrics()
    else:
        metrics = {
            "der": None,
            "jer": None,
            "num_turns": 0,
            "num_speakers": 0,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--score", type=Path)
    args = parser.parse_args()
    if args.score is not None:
        write_score(args.score)
