import hashlib
import json
import os


def file_hash(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def test_leaf_index_and_meshes_match_ground_truth():
    with open("/root/output/leaf_parts_index.json", "r", encoding="utf-8") as handle:
        produced = json.load(handle)
    with open("/root/ground_truth/leaf_parts_index.json", "r", encoding="utf-8") as handle:
        expected = json.load(handle)

    normalized_produced = {
        "leaf_part_count": produced["leaf_part_count"],
        "total_leaf_meshes": produced["total_leaf_meshes"],
        "leaf_parts": [],
    }
    normalized_expected = {
        "leaf_part_count": expected["leaf_part_count"],
        "total_leaf_meshes": expected["total_leaf_meshes"],
        "leaf_parts": [],
    }

    for item in produced["leaf_parts"]:
        assert os.path.exists(item["obj_path"])
        normalized_produced["leaf_parts"].append(
            {
                "part_name": item["part_name"],
                "ancestor_chain": item["ancestor_chain"],
                "obj_hash": file_hash(item["obj_path"]),
            }
        )

    for item in expected["leaf_parts"]:
        normalized_expected["leaf_parts"].append(
            {
                "part_name": item["part_name"],
                "ancestor_chain": item["ancestor_chain"],
                "obj_hash": file_hash(item["obj_path"]),
            }
        )

    assert normalized_produced == normalized_expected
