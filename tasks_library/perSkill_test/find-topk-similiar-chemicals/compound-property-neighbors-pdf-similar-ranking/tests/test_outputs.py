#!/usr/bin/env python3

import json
import math
import os
import sys

OUTPUT_PATH = "/root/workspace/compound_neighbors.json"
EXPECTED = {
    "source_document": "/root/compound_properties_table.dat",
    "distance_metric": "euclidean_on_minmax_normalized_columns",
    "normalized_columns": ["molecular_weight", "xlogp", "hbd", "hba", "tpsa"],
    "extracted_compound_count": 11,
    "queries": [
        {
            "target": "Acetaminophen",
            "top_k": 3,
            "neighbors": [
                {"compound": "Vanillin", "distance": 0.5790},
                {"compound": "Salicylic acid", "distance": 0.6021},
                {"compound": "Benzamide", "distance": 0.6361},
            ],
        },
        {
            "target": "Ibuprofen",
            "top_k": 4,
            "neighbors": [
                {"compound": "Naproxen", "distance": 0.5278},
                {"compound": "Phenacetin", "distance": 0.6759},
                {"compound": "Ketoprofen", "distance": 0.7588},
                {"compound": "Benzoic acid", "distance": 0.8028},
            ],
        },
    ],
}


def fail(message):
    raise AssertionError(message)


def check_neighbor_list(actual, expected):
    if len(actual) != len(expected):
        fail(f"neighbor count mismatch: expected {len(expected)}, got {len(actual)}")
    for actual_item, expected_item in zip(actual, expected):
        if actual_item.get("compound") != expected_item["compound"]:
            fail(
                "compound mismatch: "
                f"expected {expected_item['compound']}, got {actual_item.get('compound')}"
            )
        distance = actual_item.get("distance")
        if not isinstance(distance, (int, float)):
            fail(f"distance must be numeric, got {type(distance).__name__}")
        if not math.isclose(float(distance), expected_item["distance"], abs_tol=1e-4):
            fail(
                "distance mismatch for "
                f"{expected_item['compound']}: expected {expected_item['distance']}, got {distance}"
            )


def main():
    if not os.path.exists(OUTPUT_PATH):
        fail(f"missing output file: {OUTPUT_PATH}")

    with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    for key in ["source_document", "distance_metric", "normalized_columns", "extracted_compound_count", "queries"]:
        if key not in data:
            fail(f"missing top-level key: {key}")

    if data["source_document"] != EXPECTED["source_document"]:
        fail(
            "source_document mismatch: "
            f"expected {EXPECTED['source_document']}, got {data['source_document']}"
        )
    if data["distance_metric"] != EXPECTED["distance_metric"]:
        fail(
            "distance_metric mismatch: "
            f"expected {EXPECTED['distance_metric']}, got {data['distance_metric']}"
        )
    if data["normalized_columns"] != EXPECTED["normalized_columns"]:
        fail(
            "normalized_columns mismatch: "
            f"expected {EXPECTED['normalized_columns']}, got {data['normalized_columns']}"
        )
    if data["extracted_compound_count"] != EXPECTED["extracted_compound_count"]:
        fail(
            "extracted_compound_count mismatch: "
            f"expected {EXPECTED['extracted_compound_count']}, got {data['extracted_compound_count']}"
        )

    if not isinstance(data["queries"], list):
        fail("queries must be a list")
    if len(data["queries"]) != len(EXPECTED["queries"]):
        fail(f"query count mismatch: expected {len(EXPECTED['queries'])}, got {len(data['queries'])}")

    for actual_query, expected_query in zip(data["queries"], EXPECTED["queries"]):
        if actual_query.get("target") != expected_query["target"]:
            fail(
                f"target mismatch: expected {expected_query['target']}, got {actual_query.get('target')}"
            )
        if actual_query.get("top_k") != expected_query["top_k"]:
            fail(
                f"top_k mismatch for {expected_query['target']}: "
                f"expected {expected_query['top_k']}, got {actual_query.get('top_k')}"
            )
        if "neighbors" not in actual_query:
            fail(f"missing neighbors for {expected_query['target']}")
        check_neighbor_list(actual_query["neighbors"], expected_query["neighbors"])

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
        handle.write("1.0\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        os.makedirs("/logs/verifier", exist_ok=True)
        with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
            handle.write("0.0\n")
        print(str(exc), file=sys.stderr)
        sys.exit(1)
