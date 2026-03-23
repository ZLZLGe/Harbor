import hashlib
import json
import os


def obj_hash(path):
    with open(path, "r", encoding="utf-8") as handle:
        payload = handle.read()
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_manifest_matches_ground_truth():
    with open("/root/output/part_manifest.json", "r", encoding="utf-8") as handle:
        produced = json.load(handle)
    with open("/root/ground_truth/part_manifest.json", "r", encoding="utf-8") as handle:
        expected = json.load(handle)

    normalized_produced = []
    normalized_expected = []

    for item in produced["parts"]:
        assert os.path.exists(item["obj_path"])
        normalized_produced.append(
            {
                "part_name": item["part_name"],
                "mesh_names": item["mesh_names"],
                "obj_hash": obj_hash(item["obj_path"]),
            }
        )

    for item in expected["parts"]:
        normalized_expected.append(
            {
                "part_name": item["part_name"],
                "mesh_names": item["mesh_names"],
                "obj_hash": obj_hash(item["obj_path"]),
            }
        )

    assert normalized_produced == normalized_expected
