#!/usr/bin/env python3
import csv
import json
import os
from statistics import mean

import yaml

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUT_DIR", "/app/output")

RUNS_PATH = os.path.join(DATA_DIR, "stress_screen_runs.tsv")
CODEBOOK_PATH = os.path.join(DATA_DIR, "reliability_failure_codebook.yaml")
OUT_PATH = os.path.join(OUT_DIR, "reliability_failure_reason_map.json")
UNKNOWN = "UNKNOWN"

EXPECTED = {
    "REL-4001": [("200cy后 output drop，J12焊点 ring crack", "REL-TC-001")],
    "REL-4002": [("potting edge裂开, corner delam near T3", "REL-TC-002")],
    "REL-4003": [("random vibe中 J5 latch松, harness open blip", "REL-VB-101")],
    "REL-4004": [("RF shield resonance, tx power掉到0", "REL-VB-102")],
    "REL-4005": [("M4 screw backed out after z sweep", "REL-VB-103")],
    "REL-4006": [("12h hot soak后 buck reg runaway, case very hot", "REL-BI-201")],
    "REL-4007": [("fan stall alarm", "REL-BI-202"), ("airflow low", "REL-BI-202")],
    "REL-4008": [("socket A3 contact飘, move slot后pass", "REL-GN-301")],
    "REL-4009": [("像焊点老化但还没复现", UNKNOWN)],
    "REL-4010": [("fixture sense lead noise, reseat tray就好", "REL-GN-301")],
    "REL-4011": [("J12 ring crack", "REL-TC-001"), ("socket B2接触也飘", "REL-GN-301")],
    "REL-4012": [("EEPROM data drift after 24h bake", "REL-BI-203")],
    "REL-4013": [("fan stopped once at 6h, maybe tach glitch", UNKNOWN)],
    "REL-4014": [("rf shield singing", "REL-VB-102"), ("M4 screw loose", "REL-VB-103")],
    "REL-4015": [("seal leak trace, fogging inside lens", "REL-TC-003")],
}


def load_runs():
    runs = {}
    with open(RUNS_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            runs[row["run_id"]] = row
    return runs


def load_codebook():
    with open(CODEBOOK_PATH, "r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)
    labels = {}
    screens = {}
    phases = {}
    benches = {}
    for entry in payload["entries"]:
        code = entry["code"]
        labels[code] = entry["standard_label"]
        screens[code] = set(entry["allowed_screen_types"])
        phases[code] = set(entry["allowed_phases"])
        benches[code] = set(entry["allowed_benches"])
    return labels, screens, phases, benches


def load_output():
    assert os.path.exists(OUT_PATH), f"Missing output: {OUT_PATH}"
    with open(OUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def segments_of(row):
    segs = row.get("normalized_failures")
    assert isinstance(segs, list), f"normalized_failures must be a list for {row.get('run_id')}"
    return segs


def test_files_exist():
    assert os.path.exists(RUNS_PATH), f"Missing input: {RUNS_PATH}"
    assert os.path.exists(CODEBOOK_PATH), f"Missing input: {CODEBOOK_PATH}"
    assert os.path.exists(OUT_PATH), f"Missing output: {OUT_PATH}"


def test_output_shape_and_exact_coverage():
    payload = load_output()
    assert isinstance(payload, dict), "Output must be a JSON object"
    experiments = payload.get("experiments")
    assert isinstance(experiments, list), "experiments must be a list"
    assert len(experiments) == len(EXPECTED), "Output must cover every run exactly once"

    run_ids = [row.get("run_id") for row in experiments]
    assert len(run_ids) == len(set(run_ids)), "run_id must be unique"
    assert set(run_ids) == set(EXPECTED), "run_id coverage mismatch"


def test_record_fields_preserved():
    source_runs = load_runs()
    payload = load_output()
    for row in payload["experiments"]:
        src = source_runs[row["run_id"]]
        for key in [
            "program_id",
            "screen_type",
            "phase",
            "bench_id",
            "technician_id",
            "lot_id",
            "unit_sn",
            "failure_note",
            "chamber_profile",
        ]:
            assert row.get(key) == src.get(key), f"{row['run_id']} field mismatch: {key}"


def test_segments_match_expected_spans_and_codes():
    payload = load_output()
    labels, _, _, _ = load_codebook()
    for row in payload["experiments"]:
        expected_segments = EXPECTED[row["run_id"]]
        actual_segments = segments_of(row)
        assert len(actual_segments) == len(expected_segments), f"{row['run_id']} segment count mismatch"
        for idx, (segment, expected) in enumerate(zip(actual_segments, expected_segments), start=1):
            exp_span, exp_code = expected
            assert segment.get("segment_id") == f"{row['run_id']}-S{idx}", f"{row['run_id']} bad segment_id"
            assert segment.get("span_text") == exp_span, f"{row['run_id']} wrong span_text"
            assert exp_span in row["failure_note"], f"{row['run_id']} span must be exact substring"
            assert segment.get("pred_code") == exp_code, f"{row['run_id']} wrong pred_code"
            if exp_code == UNKNOWN:
                assert segment.get("pred_label") == "", f"{row['run_id']} UNKNOWN must keep empty pred_label"
            else:
                assert segment.get("pred_label") == labels[exp_code], f"{row['run_id']} wrong pred_label"


def test_scope_restrictions_are_respected():
    payload = load_output()
    _, screens, phases, benches = load_codebook()
    for row in payload["experiments"]:
        for segment in segments_of(row):
            code = segment["pred_code"]
            if code == UNKNOWN:
                continue
            assert row["screen_type"] in screens[code], f"{row['run_id']} used {code} outside allowed_screen_types"
            assert row["phase"] in phases[code], f"{row['run_id']} used {code} outside allowed_phases"
            assert row["bench_id"] in benches[code], f"{row['run_id']} used {code} outside allowed_benches"


def test_context_sensitive_cases_land_on_expected_codes():
    payload = load_output()
    by_id = {row["run_id"]: row for row in payload["experiments"]}

    assert segments_of(by_id["REL-4008"])[0]["pred_code"] == "REL-GN-301"
    assert segments_of(by_id["REL-4010"])[0]["pred_code"] == "REL-GN-301"
    assert segments_of(by_id["REL-4011"])[1]["pred_code"] == "REL-GN-301"

    assert [seg["pred_code"] for seg in segments_of(by_id["REL-4014"])] == ["REL-VB-102", "REL-VB-103"]


def test_unknown_cases_are_exact():
    payload = load_output()
    unknowns = []
    for row in payload["experiments"]:
        for segment in segments_of(row):
            if segment["pred_code"] == UNKNOWN:
                unknowns.append((row["run_id"], segment["span_text"]))
    assert unknowns == [
        ("REL-4009", "像焊点老化但还没复现"),
        ("REL-4013", "fan stopped once at 6h, maybe tach glitch"),
    ], f"Unexpected UNKNOWN segments: {unknowns}"


def test_confidence_is_numeric_rounded_and_separated():
    payload = load_output()
    known = []
    unknown = []
    for row in payload["experiments"]:
        for segment in segments_of(row):
            conf = segment.get("confidence")
            assert isinstance(conf, (int, float)), f"{row['run_id']} confidence must be numeric"
            assert 0.0 <= float(conf) <= 1.0, f"{row['run_id']} confidence out of range"
            assert round(float(conf), 4) == float(conf), f"{row['run_id']} confidence must keep 4 decimals"
            if segment["pred_code"] == UNKNOWN:
                unknown.append(float(conf))
            else:
                known.append(float(conf))
    assert known and unknown, "Need both known and UNKNOWN predictions"
    assert min(known) >= 0.62, f"Known confidence too low: {min(known):.4f}"
    assert max(unknown) <= 0.46, f"UNKNOWN confidence too high: {max(unknown):.4f}"
    assert mean(known) > mean(unknown), "Known confidence should be higher on average"


def test_rationale_mentions_screen_phase_bench_and_lot():
    payload = load_output()
    for row in payload["experiments"]:
        for segment in segments_of(row):
            rationale = str(segment.get("rationale", "")).strip()
            assert rationale, f"{row['run_id']} rationale must not be empty"
            assert f"screen={row['screen_type']}" in rationale, f"{row['run_id']} rationale missing screen_type"
            assert f"phase={row['phase']}" in rationale, f"{row['run_id']} rationale missing phase"
            assert f"bench={row['bench_id']}" in rationale, f"{row['run_id']} rationale missing bench_id"
            assert f"lot={row['lot_id']}" in rationale, f"{row['run_id']} rationale missing lot_id"


def run_all():
    tests = [
        test_files_exist,
        test_output_shape_and_exact_coverage,
        test_record_fields_preserved,
        test_segments_match_expected_spans_and_codes,
        test_scope_restrictions_are_respected,
        test_context_sensitive_cases_land_on_expected_codes,
        test_unknown_cases_are_exact,
        test_confidence_is_numeric_rounded_and_separated,
        test_rationale_mentions_screen_phase_bench_and_lot,
    ]
    for test in tests:
        test()


if __name__ == "__main__":
    run_all()
    print("all checks passed")
