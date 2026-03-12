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


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/part_audit.json"), "Output file not found"

    def _get_ground_truth(self):
        density_table = load_density_table("/root/material_density_table.md")
        triangles = parse_binary_stl("/root/audit_scan.stl")
        components = split_components(triangles)

        component_records = []
        for component in components:
            component_records.append(
                {
                    "volume": get_volume(component),
                    "material_id": component[0][3],
                }
            )

        component_records.sort(key=lambda item: item["volume"], reverse=True)
        main = component_records[0]
        debris_volume = sum(item["volume"] for item in component_records[1:])
        total_volume = main["volume"] + debris_volume

        return {
            "main_part_mass": main["volume"] * density_table[main["material_id"]],
            "material_id": main["material_id"],
            "discarded_debris_volume": debris_volume,
            "scrap_percentage": 0.0 if total_volume == 0 else debris_volume / total_volume * 100.0,
        }

    def test_values_correct(self):
        expected = self._get_ground_truth()
        with open("/root/part_audit.json", "r", encoding="utf-8") as handle:
            submission = json.load(handle)

        for key in [
            "main_part_mass",
            "material_id",
            "discarded_debris_volume",
            "scrap_percentage",
        ]:
            assert key in submission, f"Missing key: {key}"

        assert submission["material_id"] == expected["material_id"]
        assert math.isclose(
            submission["main_part_mass"],
            expected["main_part_mass"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["discarded_debris_volume"],
            expected["discarded_debris_volume"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["scrap_percentage"],
            expected["scrap_percentage"],
            rel_tol=0.001,
        )
