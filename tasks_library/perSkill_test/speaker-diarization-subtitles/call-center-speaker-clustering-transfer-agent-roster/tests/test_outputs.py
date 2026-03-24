import argparse
import json
import os
from pathlib import Path

OUTPUT_JSON = Path(os.environ.get("AGENT_VOICE_ROSTER_JSON", "/root/agent_voice_roster.json"))
INPUT_JSON = Path(os.environ.get("CALL_CENTER_INPUT_JSON", "/root/call_center_segments.json"))

EXPECTED_ASSIGNMENTS = {
    "call_001_seg_00": "cluster_00",
    "call_001_seg_01": "cluster_01",
    "call_001_seg_02": "cluster_00",
    "call_001_seg_03": "cluster_01",
    "call_002_seg_00": "cluster_02",
    "call_002_seg_01": "cluster_03",
    "call_002_seg_02": "cluster_02",
    "call_002_seg_03": "cluster_03",
    "call_003_seg_00": "cluster_00",
    "call_003_seg_01": "cluster_04",
    "call_003_seg_02": "cluster_00",
    "call_003_seg_03": "cluster_04",
    "call_004_seg_00": "cluster_05",
    "call_004_seg_01": "cluster_06",
    "call_004_seg_02": "cluster_05",
    "call_004_seg_03": "cluster_06",
    "call_005_seg_00": "cluster_02",
    "call_005_seg_01": "cluster_07",
    "call_005_seg_02": "cluster_02",
    "call_005_seg_03": "cluster_07",
    "call_006_seg_00": "cluster_05",
    "call_006_seg_01": "cluster_08",
    "call_006_seg_02": "cluster_05",
    "call_006_seg_03": "cluster_08",
}

EXPECTED_CLUSTER_TYPES = {
    "cluster_00": "agent",
    "cluster_01": "caller",
    "cluster_02": "agent",
    "cluster_03": "caller",
    "cluster_04": "caller",
    "cluster_05": "agent",
    "cluster_06": "caller",
    "cluster_07": "caller",
    "cluster_08": "caller",
}

EXPECTED_CLUSTER_CALLS = {
    "cluster_00": ["call_001", "call_003"],
    "cluster_01": ["call_001"],
    "cluster_02": ["call_002", "call_005"],
    "cluster_03": ["call_002"],
    "cluster_04": ["call_003"],
    "cluster_05": ["call_004", "call_006"],
    "cluster_06": ["call_004"],
    "cluster_07": ["call_005"],
    "cluster_08": ["call_006"],
}


def load_input_segments():
    payload = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    ordered = []
    for call in sorted(payload["calls"], key=lambda item: item["call_id"]):
        for segment in sorted(call["segments"], key=lambda item: item["segment_index"]):
            ordered.append(
                {
                    "call_id": call["call_id"],
                    "segment_id": segment["segment_id"],
                }
            )
    return payload, ordered


def load_output():
    if not OUTPUT_JSON.exists():
        raise AssertionError("missing /root/agent_voice_roster.json")
    return json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def validate():
    payload, ordered_segments = load_input_segments()
    output = load_output()

    expect(output.get("dataset_id") == payload["dataset_id"], "dataset_id mismatch")
    expect(isinstance(output.get("clusters"), list), "clusters must be a list")
    expect(isinstance(output.get("agent_roster"), list), "agent_roster must be a list")
    expect(isinstance(output.get("caller_roster"), list), "caller_roster must be a list")
    expect(isinstance(output.get("segment_assignments"), list), "segment_assignments must be a list")

    assignments = output["segment_assignments"]
    expect(len(assignments) == len(ordered_segments), "segment_assignments length mismatch")

    expected_order = [(item["call_id"], item["segment_id"]) for item in ordered_segments]
    actual_order = [(item.get("call_id"), item.get("segment_id")) for item in assignments]
    expect(actual_order == expected_order, "segment_assignments must follow call_id/segment_index order")

    seen_segment_ids = set()
    actual_assignments = {}
    for item in assignments:
        segment_id = item.get("segment_id")
        cluster_id = item.get("cluster_id")
        speaker_type = item.get("speaker_type")
        expect(segment_id not in seen_segment_ids, f"duplicate assignment for {segment_id}")
        expect(segment_id in EXPECTED_ASSIGNMENTS, f"unknown segment_id {segment_id}")
        expect(cluster_id in EXPECTED_CLUSTER_TYPES, f"unexpected cluster_id {cluster_id}")
        expect(speaker_type == EXPECTED_CLUSTER_TYPES[cluster_id], f"speaker_type mismatch for {segment_id}")
        seen_segment_ids.add(segment_id)
        actual_assignments[segment_id] = cluster_id

    expect(actual_assignments == EXPECTED_ASSIGNMENTS, "segment-to-cluster assignment mismatch")

    clusters = output["clusters"]
    expect(len(clusters) == len(EXPECTED_CLUSTER_TYPES), "unexpected number of clusters")
    cluster_map = {}
    for cluster in clusters:
        cluster_id = cluster.get("cluster_id")
        expect(cluster_id in EXPECTED_CLUSTER_TYPES, f"unexpected cluster entry {cluster_id}")
        expect(cluster_id not in cluster_map, f"duplicate cluster entry {cluster_id}")
        cluster_map[cluster_id] = cluster

        expected_call_ids = EXPECTED_CLUSTER_CALLS[cluster_id]
        expected_segment_ids = sorted(
            segment_id for segment_id, expected_cluster_id in EXPECTED_ASSIGNMENTS.items() if expected_cluster_id == cluster_id
        )
        expect(cluster.get("speaker_type") == EXPECTED_CLUSTER_TYPES[cluster_id], f"cluster speaker_type mismatch for {cluster_id}")
        expect(cluster.get("call_ids") == expected_call_ids, f"cluster call_ids mismatch for {cluster_id}")
        expect(cluster.get("distinct_call_count") == len(expected_call_ids), f"distinct_call_count mismatch for {cluster_id}")
        expect(cluster.get("segment_ids") == expected_segment_ids, f"segment_ids mismatch for {cluster_id}")
        expect(cluster.get("segment_count") == len(expected_segment_ids), f"segment_count mismatch for {cluster_id}")

    expected_agent_ids = [cluster_id for cluster_id, speaker_type in EXPECTED_CLUSTER_TYPES.items() if speaker_type == "agent"]
    expected_caller_ids = [cluster_id for cluster_id, speaker_type in EXPECTED_CLUSTER_TYPES.items() if speaker_type == "caller"]

    expect([item.get("cluster_id") for item in output["agent_roster"]] == expected_agent_ids, "agent_roster cluster order mismatch")
    expect([item.get("cluster_id") for item in output["caller_roster"]] == expected_caller_ids, "caller_roster cluster order mismatch")

    for roster_name, roster_entries in [("agent_roster", output["agent_roster"]), ("caller_roster", output["caller_roster"])]:
        for entry in roster_entries:
            cluster_id = entry.get("cluster_id")
            cluster = cluster_map[cluster_id]
            expect(entry.get("call_ids") == cluster["call_ids"], f"{roster_name} call_ids mismatch for {cluster_id}")
            expect(entry.get("segment_count") == cluster["segment_count"], f"{roster_name} segment_count mismatch for {cluster_id}")

    threshold = output.get("distance_threshold")
    expect(isinstance(threshold, (int, float)), "distance_threshold must be numeric")
    expect(0 < float(threshold) < 1, "distance_threshold must be in (0, 1)")

    return {
        "dataset_id": output["dataset_id"],
        "cluster_count": len(clusters),
        "agent_cluster_count": len(output["agent_roster"]),
        "caller_cluster_count": len(output["caller_roster"]),
        "all_assignments_correct": True,
    }


def pairwise_f1(actual_assignments):
    segment_ids = sorted(EXPECTED_ASSIGNMENTS)
    true_positive = 0
    false_positive = 0
    false_negative = 0
    for left_index, left_segment in enumerate(segment_ids):
        for right_segment in segment_ids[left_index + 1 :]:
            expected_same = EXPECTED_ASSIGNMENTS[left_segment] == EXPECTED_ASSIGNMENTS[right_segment]
            actual_same = actual_assignments.get(left_segment) == actual_assignments.get(right_segment)
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


def write_score(score_path: Path):
    payload, ordered_segments = load_input_segments()
    result = {
        "dataset_id": payload["dataset_id"],
        "output_exists": OUTPUT_JSON.exists(),
        "segment_count": len(ordered_segments),
        "cluster_count": 0,
        "pairwise_f1": 0.0,
        "all_assignments_correct": False,
    }
    if OUTPUT_JSON.exists():
        try:
            output = load_output()
            result["cluster_count"] = len(output.get("clusters", []))
            actual_assignments = {
                item.get("segment_id"): item.get("cluster_id")
                for item in output.get("segment_assignments", [])
                if isinstance(item, dict)
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
