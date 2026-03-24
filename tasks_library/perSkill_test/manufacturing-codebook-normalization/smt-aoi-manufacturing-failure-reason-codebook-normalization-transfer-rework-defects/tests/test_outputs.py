#!/usr/bin/env python3
import csv
import json
import os
import re
from typing import Any, Dict, List

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUT_DIR", "/app/output")

OUT_PATH = os.path.join(OUT_DIR, "aoi_defect_map.json")
CASES_PATH = os.path.join(DATA_DIR, "aoi_cases.jsonl")
CODEBOOK_PATH = os.path.join(DATA_DIR, "aoi_defect_codebook.csv")

COMP_RE = re.compile(r"\b([A-Z]{1,3}\d{1,4})\b", re.IGNORECASE)

EXPECTED = {
    "A1001": [("U12 pin5-6 bridge / 连锡", "SMT-AOI-001")],
    "A1002": [("R88 少锡", "SMT-AOI-002"), ("C41 虚焊", "SMT-AOI-003")],
    "A1003": [("C210 polarity rev / C210 反向", "SMT-AOI-006")],
    "A1004": [("R45 tombstone / 立碑", "SMT-AOI-004")],
    "A1005": [("Q3 偏位 offset to east", "SMT-AOI-007")],
    "A1006": [("D8 no part / 漏件", "SMT-AOI-005")],
    "A1007": [("R120 wrong value loaded, mark 102 not 103", "SMT-AOI-008")],
    "A1008": [("U7 pin1~2 bridge", "SMT-AOI-001"), ("solder ball nearby", "SMT-AOI-009")],
    "A1009": [("after rework C33 pad lift, copper exposed", "SMT-AOI-010")],
    "A1010": [("flux残留 around U5, sticky after clean", "SMT-AOI-011")],
    "A1011": [("R19 tombstone again after rework", "UNKNOWN")],
    "A1012": [("C78 shifted / 偏位 before oven", "SMT-AOI-007")],
    "A1013": [("L4 missing before reflow", "SMT-AOI-005")],
    "A1014": [("looks dull, maybe heat mark only", "UNKNOWN")],
    "A1015": [("D11 reversed", "SMT-AOI-006"), ("R44 missing", "SMT-AOI-005")],
}


def load_json(path: str) -> Any:
    assert os.path.exists(path), f"Missing file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_cases() -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    assert os.path.exists(CASES_PATH), f"Missing input: {CASES_PATH}"
    with open(CASES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                out[row["board_id"]] = row
    return out


def load_codebook() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    assert os.path.exists(CODEBOOK_PATH), f"Missing input: {CODEBOOK_PATH}"
    with open(CODEBOOK_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["code"]] = {
                "label": row["standard_label"],
                "allowed_stages": {x.strip() for x in row["allowed_stages"].split(";") if x.strip()},
            }
    return out


def test_required_files_exist():
    assert os.path.exists(OUT_PATH), f"Missing output: {OUT_PATH}"
    assert os.path.exists(CASES_PATH), f"Missing input: {CASES_PATH}"
    assert os.path.exists(CODEBOOK_PATH), f"Missing input: {CODEBOOK_PATH}"


def test_output_shape_and_coverage():
    payload = load_json(OUT_PATH)
    assert isinstance(payload, dict), "Output must be a JSON object"
    boards = payload.get("boards")
    assert isinstance(boards, list), "boards must be a list"
    assert len(boards) == len(EXPECTED), "Output must cover every input board exactly once"

    ids = [row.get("board_id") for row in boards]
    assert len(set(ids)) == len(ids), "Duplicate board_id found"
    assert set(ids) == set(EXPECTED), "board_id coverage mismatch"


def test_board_fields_preserved():
    payload = load_json(OUT_PATH)
    cases = load_cases()

    for row in payload["boards"]:
        src = cases[row["board_id"]]
        for key in [
            "panel_id",
            "product_family",
            "process_stage",
            "line",
            "side",
            "operator_id",
            "remark_text",
        ]:
            assert row.get(key) == src.get(key), f"{row['board_id']} field mismatch: {key}"


def test_segments_match_expected_codes_and_spans():
    payload = load_json(OUT_PATH)
    codebook = load_codebook()

    for row in payload["boards"]:
        board_id = row["board_id"]
        expected_segments = EXPECTED[board_id]
        actual_segments = row.get("defect_segments")

        assert isinstance(actual_segments, list), f"{board_id} defect_segments must be a list"
        assert len(actual_segments) == len(expected_segments), f"{board_id} segment count mismatch"

        for idx, (segment, expected) in enumerate(zip(actual_segments, expected_segments), start=1):
            expected_span, expected_code = expected
            assert segment.get("segment_id") == f"{board_id}-S{idx}", f"{board_id} bad segment_id"
            assert segment.get("span_text") == expected_span, f"{board_id} bad span_text at segment {idx}"
            assert expected_span in row["remark_text"], f"{board_id} span is not substring of remark_text"
            assert segment.get("pred_code") == expected_code, f"{board_id} wrong pred_code at segment {idx}"

            label = segment.get("pred_label")
            if expected_code == "UNKNOWN":
                assert label == "", f"{board_id} UNKNOWN must have empty pred_label"
            else:
                assert label == codebook[expected_code]["label"], f"{board_id} pred_label mismatch"


def test_stage_restrictions_respected():
    payload = load_json(OUT_PATH)
    codebook = load_codebook()

    for row in payload["boards"]:
        stage = row["process_stage"]
        for segment in row["defect_segments"]:
            code = segment["pred_code"]
            if code == "UNKNOWN":
                continue
            assert stage in codebook[code]["allowed_stages"], f"{row['board_id']} used {code} outside allowed_stages"


def test_unknown_cases_are_targeted():
    payload = load_json(OUT_PATH)
    unknown_segments = []
    for row in payload["boards"]:
        for segment in row["defect_segments"]:
            if segment["pred_code"] == "UNKNOWN":
                unknown_segments.append((row["board_id"], segment["span_text"]))

    assert unknown_segments == [
        ("A1011", "R19 tombstone again after rework"),
        ("A1014", "looks dull, maybe heat mark only"),
    ], f"Unexpected UNKNOWN segments: {unknown_segments}"


def test_confidence_is_numeric_and_separated():
    payload = load_json(OUT_PATH)
    known: List[float] = []
    unknown: List[float] = []

    for row in payload["boards"]:
        for segment in row["defect_segments"]:
            conf = segment.get("confidence")
            assert isinstance(conf, (int, float)), f"{row['board_id']} confidence must be numeric"
            assert 0.0 <= float(conf) <= 1.0, f"{row['board_id']} confidence out of range"
            assert round(float(conf), 4) == float(conf), f"{row['board_id']} confidence must keep 4 decimals"
            if segment["pred_code"] == "UNKNOWN":
                unknown.append(float(conf))
            else:
                known.append(float(conf))

    assert known, "Need at least one known defect"
    assert unknown, "Need at least one UNKNOWN defect"
    assert min(known) >= 0.62, f"Known confidence too low: {min(known):.4f}"
    assert max(unknown) <= 0.55, f"UNKNOWN confidence too high: {max(unknown):.4f}"


def test_rationale_is_grounded():
    payload = load_json(OUT_PATH)

    for row in payload["boards"]:
        stage = row["process_stage"].lower()
        for segment in row["defect_segments"]:
            rationale = str(segment.get("rationale", ""))
            assert rationale, f"{row['board_id']} missing rationale"
            assert f"stage={row['process_stage']}" in rationale, f"{row['board_id']} rationale missing stage"

            span = segment["span_text"]
            match = COMP_RE.search(span)
            if match:
                comp = match.group(1).upper()
                assert f"comp={comp}" in rationale, f"{row['board_id']} rationale missing component {comp}"

