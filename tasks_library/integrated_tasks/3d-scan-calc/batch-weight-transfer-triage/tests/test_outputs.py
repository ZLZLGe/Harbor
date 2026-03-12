import collections
import json
import math
import os
import re
import struct


def load_density_table(path):
    table = {}
    pattern = re.compile(r"^\|\s*\*\*(\d+)\*\*\s*\|[^|]*\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|")
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.match(line.strip())
            if match:
                table[int(match.group(1))] = float(match.group(2))
    return table


def load_policy(path):
    approved_ids = []
    max_mass = None
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            id_match = re.match(r"^-\s*`(\d+)`$", line)
            if id_match:
                approved_ids.append(int(id_match.group(1)))
            mass_match = re.search(r"`([0-9]+(?:\.[0-9]+)?)\s*g`", line)
            if mass_match:
                max_mass = float(mass_match.group(1))
    return set(approved_ids), max_mass


def parse_binary_stl(path):
    triangles = []
    with open(path, "rb") as handle:
        handle.read(80)
        count = struct.unpack("<I", handle.read(4))[0]
        for _ in range(count):
            data = handle.read(50)
            floats = struct.unpack("<3f3f3f3f", data[:48])
            attr = struct.unpack("<H", data[48:50])[0]
            v1 = (floats[3], floats[4], floats[5])
            v2 = (floats[6], floats[7], floats[8])
            v3 = (floats[9], floats[10], floats[11])
            triangles.append((v1, v2, v3, attr))
    return triangles


def quantize(vertex):
    return (round(vertex[0], 5), round(vertex[1], 5), round(vertex[2], 5))


def split_components(triangles):
    vertex_map = collections.defaultdict(list)
    for index, triangle in enumerate(triangles):
        for vertex in triangle[:3]:
            vertex_map[quantize(vertex)].append(index)

    visited = set()
    components = []
    for index in range(len(triangles)):
        if index in visited:
            continue
        queue = collections.deque([index])
        visited.add(index)
        component_indices = []
        while queue:
            current = queue.popleft()
            component_indices.append(current)
            for vertex in triangles[current][:3]:
                for neighbor in vertex_map[quantize(vertex)]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
        components.append([triangles[item] for item in component_indices])
    return components


def get_volume(triangles):
    total = 0.0
    for triangle in triangles:
        v1, v2, v3 = triangle[0], triangle[1], triangle[2]
        cp_x = v2[1] * v3[2] - v2[2] * v3[1]
        cp_y = v2[2] * v3[0] - v2[0] * v3[2]
        cp_z = v2[0] * v3[1] - v2[1] * v3[0]
        total += v1[0] * cp_x + v1[1] * cp_y + v1[2] * cp_z
    return abs(total) / 6.0


def build_expected_records():
    density_table = load_density_table("/root/material_density_table.md")
    approved_ids, max_mass = load_policy("/root/batch_acceptance_rules.md")
    records = []
    for name in sorted(os.listdir("/root/scan_batch")):
        if not name.endswith(".stl"):
            continue
        triangles = parse_binary_stl(os.path.join("/root/scan_batch", name))
        components = split_components(triangles)
        components.sort(key=get_volume, reverse=True)
        main = components[0]
        main_volume = get_volume(main)
        material_id = main[0][3]
        mass = main_volume * density_table[material_id]
        records.append(
            {
                "file": name,
                "main_part_mass": mass,
                "material_id": material_id,
                "acceptable": material_id in approved_ids and mass <= max_mass,
            }
        )
    records.sort(key=lambda item: (-item["main_part_mass"], item["file"]))
    return records


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/batch_triage.json"), "Output file not found"

    def test_values_correct(self):
        expected_records = build_expected_records()
        expected_acceptable = [item for item in expected_records if item["acceptable"]]
        assert expected_acceptable, "Fixture expected at least one acceptable part"

        with open("/root/batch_triage.json", "r", encoding="utf-8") as handle:
            submission = json.load(handle)

        assert "heaviest_acceptable" in submission
        assert "ranked_parts" in submission
        assert isinstance(submission["ranked_parts"], list)
        assert len(submission["ranked_parts"]) == len(expected_records)

        for actual, expected in zip(submission["ranked_parts"], expected_records):
            for key in ["file", "main_part_mass", "material_id", "acceptable"]:
                assert key in actual, f"Missing key in ranked_parts entry: {key}"
            assert actual["file"] == expected["file"]
            assert actual["material_id"] == expected["material_id"]
            assert actual["acceptable"] == expected["acceptable"]
            assert math.isclose(
                actual["main_part_mass"],
                expected["main_part_mass"],
                rel_tol=0.001,
            )

        heaviest = submission["heaviest_acceptable"]
        expected_heaviest = expected_acceptable[0]
        for key in ["file", "main_part_mass", "material_id"]:
            assert key in heaviest, f"Missing key in heaviest_acceptable: {key}"
        assert heaviest["file"] == expected_heaviest["file"]
        assert heaviest["material_id"] == expected_heaviest["material_id"]
        assert math.isclose(
            heaviest["main_part_mass"],
            expected_heaviest["main_part_mass"],
            rel_tol=0.001,
        )
