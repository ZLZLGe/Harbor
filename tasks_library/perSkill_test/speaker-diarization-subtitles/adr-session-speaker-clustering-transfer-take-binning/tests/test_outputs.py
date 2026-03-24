import argparse
import csv
import json
import os
from pathlib import Path

OUTPUT_TSV = Path(os.environ.get("ADR_TAKE_BINS_TSV", "/root/adr_take_bins.tsv"))
INPUT_JSON = Path(os.environ.get("ADR_SESSION_INPUT_JSON", "/root/adr_session_takes.json"))

EXPECTED_FIELDNAMES = [
    "session_id",
    "actor_bin_id",
    "take_id",
    "cue_id",
    "slate",
    "record_order",
    "start_tc",
    "end_tc",
    "duration_sec",
    "pickup_group",
    "guide_track_ref",
    "bin_take_index",
]

EXPECTED_ASSIGNMENTS = {
    "take_001": "actor_bin_00",
    "take_002": "actor_bin_01",
    "take_003": "actor_bin_02",
    "take_004": "actor_bin_03",
    "take_005": "actor_bin_00",
    "take_006": "actor_bin_02",
    "take_007": "actor_bin_01",
    "take_008": "actor_bin_03",
    "take_009": "actor_bin_00",
    "take_010": "actor_bin_02",
    "take_011": "actor_bin_01",
    "take_012": "actor_bin_03",
    "take_013": "actor_bin_00",
    "take_014": "actor_bin_01",
    "take_015": "actor_bin_02",
    "take_016": "actor_bin_03",
}

EXPECTED_BIN_INDEX = {
    "take_001": "1",
    "take_005": "2",
    "take_009": "3",
    "take_013": "4",
    "take_002": "1",
    "take_007": "2",
    "take_011": "3",
    "take_014": "4",
    "take_003": "1",
    "take_006": "2",
    "take_010": "3",
    "take_015": "4",
    "take_004": "1",
    "take_008": "2",
    "take_012": "3",
    "take_016": "4",
}


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def load_input():
    payload = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    takes = sorted(payload["takes"], key=lambda item: item["record_order"])
    return payload, takes


def load_output_rows():
    expect(OUTPUT_TSV.exists(), "missing /root/adr_take_bins.tsv")
    with OUTPUT_TSV.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        expect(reader.fieldnames == EXPECTED_FIELDNAMES, "unexpected TSV header")
        return list(reader)


def pairwise_f1(actual_assignments):
    take_ids = sorted(EXPECTED_ASSIGNMENTS)
    true_positive = 0
    false_positive = 0
    false_negative = 0
    for left_index, left_take in enumerate(take_ids):
        for right_take in take_ids[left_index + 1 :]:
            expected_same = EXPECTED_ASSIGNMENTS[left_take] == EXPECTED_ASSIGNMENTS[right_take]
            actual_same = actual_assignments.get(left_take) == actual_assignments.get(right_take)
            if actual_same and expected_same:
                true_positive += 1
            elif actual_same and not expected_same:
                false_positive += 1
            elif not actual_same and expected_same:
                false_negative += 1
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def validate():
    payload, takes = load_input()
    rows = load_output_rows()

    expect(len(rows) == len(takes), "row count must match take count")
    expect(payload["actor_count"] == 4, "test fixture expects exactly 4 actors")

    actual_assignments = {}
    seen_take_ids = set()

    for row, take in zip(rows, takes):
        take_id = row["take_id"]
        expect(take_id == take["take_id"], f"rows must follow record_order; expected {take['take_id']}, got {take_id}")
        expect(take_id not in seen_take_ids, f"duplicate take_id {take_id}")
        seen_take_ids.add(take_id)

        expect(row["session_id"] == payload["session_id"], f"session_id mismatch for {take_id}")
        expect(row["actor_bin_id"] in {"actor_bin_00", "actor_bin_01", "actor_bin_02", "actor_bin_03"}, f"bad actor_bin_id for {take_id}")
        expect(row["cue_id"] == take["cue_id"], f"cue_id mismatch for {take_id}")
        expect(row["slate"] == take["slate"], f"slate mismatch for {take_id}")
        expect(row["record_order"] == str(take["record_order"]), f"record_order mismatch for {take_id}")
        expect(row["start_tc"] == take["start_tc"], f"start_tc mismatch for {take_id}")
        expect(row["end_tc"] == take["end_tc"], f"end_tc mismatch for {take_id}")
        expect(row["duration_sec"] == f"{float(take['duration_sec']):.2f}", f"duration_sec mismatch for {take_id}")
        expect(row["pickup_group"] == take["pickup_group"], f"pickup_group mismatch for {take_id}")
        expect(row["guide_track_ref"] == take["guide_track_ref"], f"guide_track_ref mismatch for {take_id}")
        expect(row["bin_take_index"] == EXPECTED_BIN_INDEX[take_id], f"bin_take_index mismatch for {take_id}")

        actual_assignments[take_id] = row["actor_bin_id"]

    expect(actual_assignments == EXPECTED_ASSIGNMENTS, "take-to-bin assignment mismatch")

    per_bin_orders = {}
    for row in rows:
        per_bin_orders.setdefault(row["actor_bin_id"], []).append(int(row["record_order"]))
    expect(sorted(per_bin_orders) == ["actor_bin_00", "actor_bin_01", "actor_bin_02", "actor_bin_03"], "unexpected bin ids")
    expect(min(per_bin_orders["actor_bin_00"]) == 1, "actor_bin_00 must contain earliest record_order 1")
    expect(min(per_bin_orders["actor_bin_01"]) == 2, "actor_bin_01 must contain earliest record_order 2")
    expect(min(per_bin_orders["actor_bin_02"]) == 3, "actor_bin_02 must contain earliest record_order 3")
    expect(min(per_bin_orders["actor_bin_03"]) == 4, "actor_bin_03 must contain earliest record_order 4")
    for actor_bin_id, record_orders in per_bin_orders.items():
        expect(len(record_orders) == 4, f"{actor_bin_id} must contain exactly 4 takes")
        expect(record_orders == sorted(record_orders), f"{actor_bin_id} rows must stay in record_order")

    return {
        "session_id": payload["session_id"],
        "take_count": len(takes),
        "bin_count": len(per_bin_orders),
        "all_assignments_correct": True,
    }


def write_score(score_path: Path):
    payload, takes = load_input()
    result = {
        "session_id": payload["session_id"],
        "output_exists": OUTPUT_TSV.exists(),
        "take_count": len(takes),
        "pairwise_f1": 0.0,
        "all_assignments_correct": False,
    }
    if OUTPUT_TSV.exists():
        try:
            rows = load_output_rows()
            actual_assignments = {
                row["take_id"]: row["actor_bin_id"]
                for row in rows
                if row.get("take_id")
            }
            result["pairwise_f1"] = round(pairwise_f1(actual_assignments), 6)
            result["all_assignments_correct"] = actual_assignments == EXPECTED_ASSIGNMENTS
        except Exception as exc:
            result["error"] = str(exc)
    score_path.parent.mkdir(parents=True, exist_ok=True)
    score_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--score", type=Path)
    args = parser.parse_args()
    if args.score is not None:
        write_score(args.score)
        return
    validate()


if __name__ == "__main__":
    main()
