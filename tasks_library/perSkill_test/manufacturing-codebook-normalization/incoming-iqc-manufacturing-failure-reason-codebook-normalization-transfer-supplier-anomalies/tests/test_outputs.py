#!/usr/bin/env python3
import csv
import json
import os
from statistics import mean

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUT_DIR", "/app/output")

LOTS_PATH = os.path.join(DATA_DIR, "iqc_supplier_lots.csv")
CODEBOOK_PATH = os.path.join(DATA_DIR, "material_defect_codebook.json")
OUT_PATH = os.path.join(OUT_DIR, "iqc_supplier_reason_map.json")
UNKNOWN = "UNKNOWN"

EXPECTED = {
    "IQC-3001": [("板边绿油刮伤见铜", "IQC-MAT-001"), ("左下角有粉尘", "IQC-MAT-012")],
    "IQC-3002": [("端子发黑氧化 contact dull", "IQC-MAT-002")],
    "IQC-3003": [("壳体角位 crack chip", "IQC-MAT-003")],
    "IQC-3004": [("外箱rev sticker错版 wrong rev label", "IQC-MAT-004")],
    "IQC-3005": [("每箱少2pcs spacer", "IQC-MAT-005")],
    "IQC-3006": [("pin coplanarity 高 0.22mm", "IQC-MAT-006")],
    "IQC-3007": [("镀层起泡 peel off around rim", "IQC-MAT-011")],
    "IQC-3008": [("inside bag有毛丝异物 contamination", "IQC-MAT-012")],
    "IQC-3009": [("black pin again wetting poor", "IQC-MAT-002")],
    "IQC-3010": [("core width oversize +0.25mm", "IQC-MAT-006")],
    "IQC-3011": [("vacuum bag broken HIC pink", "IQC-MAT-007")],
    "IQC-3012": [("polar mark reverse 正负标反", "IQC-MAT-008")],
    "IQC-3013": [("2 pins bent歪脚", "IQC-MAT-010")],
    "IQC-3014": [("edge burr sharp cut hand risk", "IQC-MAT-009")],
    "IQC-3015": [("字迹淡 maybe old stock label", UNKNOWN)],
    "IQC-3016": [("seal bag OK but carton bruised", UNKNOWN)],
    "IQC-3017": [("外箱rev sticker错版", "IQC-MAT-004"), ("每箱少1pcs tray", "IQC-MAT-005")],
}


def load_json(path):
    assert os.path.exists(path), f"Missing file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_lots():
    rows = {}
    with open(LOTS_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[row["inspection_id"]] = row
    return rows


def load_codebook():
    payload = load_json(CODEBOOK_PATH)
    labels = {}
    category_scope = {}
    stage_scope = {}
    for entry in payload["entries"]:
        labels[entry["code"]] = entry["standard_label"]
        category_scope[entry["code"]] = set(entry["allowed_categories"])
        stage_scope[entry["code"]] = set(entry["allowed_stages"])
    return labels, category_scope, stage_scope


def load_output():
    return load_json(OUT_PATH)


def segments_of(row):
    segs = row.get("normalized_reasons")
    assert isinstance(segs, list), f"normalized_reasons must be a list for {row.get('inspection_id')}"
    return segs


def test_required_files_exist():
    assert os.path.exists(OUT_PATH), f"Missing output: {OUT_PATH}"
    assert os.path.exists(LOTS_PATH), f"Missing input: {LOTS_PATH}"
    assert os.path.exists(CODEBOOK_PATH), f"Missing input: {CODEBOOK_PATH}"


def test_output_shape_and_exact_coverage():
    payload = load_output()
    assert isinstance(payload, dict), "Output must be a JSON object"
    lots = payload.get("lots")
    assert isinstance(lots, list), "lots must be a list"
    assert len(lots) == len(EXPECTED), "Output must cover every input inspection exactly once"

    ids = [row.get("inspection_id") for row in lots]
    assert len(ids) == len(set(ids)), "inspection_id must be unique"
    assert set(ids) == set(EXPECTED), "inspection_id coverage mismatch"


def test_record_fields_preserved():
    source_rows = load_lots()
    payload = load_output()
    for row in payload["lots"]:
        src = source_rows[row["inspection_id"]]
        for key in [
            "supplier_id",
            "supplier_lot",
            "material_code",
            "item_category",
            "inspection_stage",
            "inspector_id",
            "defect_remark",
        ]:
            assert row.get(key) == src.get(key), f"{row['inspection_id']} field mismatch: {key}"
        assert row.get("sample_size") == int(src["sample_size"]), f"{row['inspection_id']} sample_size mismatch"


def test_segments_match_expected_spans_and_codes():
    payload = load_output()
    labels, _, _ = load_codebook()
    for row in payload["lots"]:
        expected = EXPECTED[row["inspection_id"]]
        actual = segments_of(row)
        assert len(actual) == len(expected), f"{row['inspection_id']} segment count mismatch"
        for idx, (segment, exp) in enumerate(zip(actual, expected), start=1):
            exp_span, exp_code = exp
            assert segment.get("segment_id") == f"{row['inspection_id']}-S{idx}"
            assert segment.get("span_text") == exp_span, f"{row['inspection_id']} wrong span_text"
            assert exp_span in row["defect_remark"], f"{row['inspection_id']} span must be exact substring"
            assert segment.get("pred_code") == exp_code, f"{row['inspection_id']} wrong pred_code"
            if exp_code == UNKNOWN:
                assert segment.get("pred_label") == "", f"{row['inspection_id']} UNKNOWN must keep empty pred_label"
            else:
                assert segment.get("pred_label") == labels[exp_code], f"{row['inspection_id']} wrong pred_label"


def test_category_and_stage_scope_respected():
    payload = load_output()
    _, category_scope, stage_scope = load_codebook()
    for row in payload["lots"]:
        category = row["item_category"]
        stage = row["inspection_stage"]
        for segment in segments_of(row):
            code = segment["pred_code"]
            if code == UNKNOWN:
                continue
            assert category in category_scope[code], f"{row['inspection_id']} used {code} outside allowed_categories"
            assert stage in stage_scope[code], f"{row['inspection_id']} used {code} outside allowed_stages"


def test_supplier_lot_context_cases_are_consistent():
    payload = load_output()
    by_id = {row["inspection_id"]: row for row in payload["lots"]}

    lot_pair = [by_id["IQC-3002"], by_id["IQC-3009"]]
    pair_codes = [segments_of(row)[0]["pred_code"] for row in lot_pair]
    assert pair_codes == ["IQC-MAT-002", "IQC-MAT-002"], "Repeated supplier lot should resolve to the same oxidation code"

    mixed_pack = by_id["IQC-3017"]
    assert [seg["pred_code"] for seg in segments_of(mixed_pack)] == ["IQC-MAT-004", "IQC-MAT-005"]


def test_unknown_cases_are_targeted():
    payload = load_output()
    unknowns = []
    for row in payload["lots"]:
        for segment in segments_of(row):
            if segment["pred_code"] == UNKNOWN:
                unknowns.append((row["inspection_id"], segment["span_text"]))
    assert unknowns == [
        ("IQC-3015", "字迹淡 maybe old stock label"),
        ("IQC-3016", "seal bag OK but carton bruised"),
    ], f"Unexpected UNKNOWN segments: {unknowns}"


def test_confidence_is_numeric_rounded_and_separated():
    payload = load_output()
    known = []
    unknown = []
    for row in payload["lots"]:
        for segment in segments_of(row):
            conf = segment.get("confidence")
            assert isinstance(conf, (int, float)), f"{row['inspection_id']} confidence must be numeric"
            assert 0.0 <= float(conf) <= 1.0, f"{row['inspection_id']} confidence out of range"
            assert round(float(conf), 4) == float(conf), f"{row['inspection_id']} confidence must keep 4 decimals"
            if segment["pred_code"] == UNKNOWN:
                unknown.append(float(conf))
            else:
                known.append(float(conf))
    assert known and unknown, "Need both known and UNKNOWN cases"
    assert min(known) >= 0.72, f"Known confidence too low: {min(known):.4f}"
    assert max(unknown) <= 0.45, f"UNKNOWN confidence too high: {max(unknown):.4f}"
    assert mean(known) > mean(unknown), "Known confidence should be higher on average"


def test_rationale_mentions_category_stage_and_lot():
    payload = load_output()
    for row in payload["lots"]:
        for segment in segments_of(row):
            rationale = str(segment.get("rationale", "")).strip()
            assert rationale, f"{row['inspection_id']} rationale must not be empty"
            assert f"category={row['item_category']}" in rationale, f"{row['inspection_id']} rationale missing category"
            assert f"stage={row['inspection_stage']}" in rationale, f"{row['inspection_id']} rationale missing stage"
            assert f"lot={row['supplier_lot']}" in rationale, f"{row['inspection_id']} rationale missing supplier_lot"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
