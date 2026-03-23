import hashlib
import os


def file_hash(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def test_urdf_matches_ground_truth():
    with open("/root/output/inspection_rig.urdf", "r", encoding="utf-8") as handle:
        produced = handle.read()
    with open("/root/ground_truth/inspection_rig.urdf", "r", encoding="utf-8") as handle:
        expected = handle.read()
    assert produced == expected


def test_mesh_pack_matches_ground_truth():
    expected_files = sorted(os.listdir("/root/ground_truth/meshes"))
    produced_files = sorted(os.listdir("/root/output/meshes"))
    assert produced_files == expected_files

    for filename in expected_files:
        assert file_hash(f"/root/output/meshes/{filename}") == file_hash(
            f"/root/ground_truth/meshes/{filename}"
        )
