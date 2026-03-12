import collections
import json
import math
import os
import re
import struct


def _load_density_table():
    densities = {}
    with open("/root/material_density_table.md", encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"\|\s*\**(\d+)\**\s*\|\s*[^|]+\|\s*([0-9.]+)\s*\|", line)
            if match:
                densities[int(match.group(1))] = float(match.group(2))
    return densities


def _parse_binary_stl(path):
    triangles = []
    with open(path, "rb") as handle:
        handle.read(80)
        triangle_count = struct.unpack("<I", handle.read(4))[0]
        for _ in range(triangle_count):
            data = handle.read(50)
            floats = struct.unpack("<3f3f3f3f", data[:48])
            attribute = struct.unpack("<H", data[48:50])[0]
            vertex_1 = (floats[3], floats[4], floats[5])
            vertex_2 = (floats[6], floats[7], floats[8])
            vertex_3 = (floats[9], floats[10], floats[11])
            triangles.append((vertex_1, vertex_2, vertex_3, attribute))
    return triangles


def _connected_components(triangles):
    def quantize(vertex):
        return (round(vertex[0], 5), round(vertex[1], 5), round(vertex[2], 5))

    vertex_map = collections.defaultdict(list)
    for index, triangle in enumerate(triangles):
        for vertex in triangle[:3]:
            vertex_map[quantize(vertex)].append(index)

    components = []
    visited = set()

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

        components.append([triangles[i] for i in component_indices])

    return components


def _volume(triangles):
    total = 0.0
    for triangle in triangles:
        vertex_1, vertex_2, vertex_3 = triangle[:3]
        cross_x = vertex_2[1] * vertex_3[2] - vertex_2[2] * vertex_3[1]
        cross_y = vertex_2[2] * vertex_3[0] - vertex_2[0] * vertex_3[2]
        cross_z = vertex_2[0] * vertex_3[1] - vertex_2[1] * vertex_3[0]
        total += vertex_1[0] * cross_x + vertex_1[1] * cross_y + vertex_1[2] * cross_z
    return abs(total) / 6.0


def _largest_component_report(path):
    components = _connected_components(_parse_binary_stl(path))
    component_data = []

    for component in components:
        component_data.append(
            {
                "volume_cm3": _volume(component),
                "material_id": component[0][3],
            }
        )

    component_data.sort(key=lambda item: item["volume_cm3"], reverse=True)
    return component_data[0]


def _ground_truth():
    densities = _load_density_table()

    pre = _largest_component_report("/root/pre_machining_scan.stl")
    post = _largest_component_report("/root/post_machining_scan.stl")

    assert pre["material_id"] == post["material_id"]
    density = densities[pre["material_id"]]
    pre_mass = pre["volume_cm3"] * density
    post_mass = post["volume_cm3"] * density

    return {
        "material_id": pre["material_id"],
        "pre_machining_volume_cm3": pre["volume_cm3"],
        "post_machining_volume_cm3": post["volume_cm3"],
        "pre_machining_mass_g": pre_mass,
        "post_machining_mass_g": post_mass,
        "removed_mass_g": pre_mass - post_mass,
        "yield_percentage": (post_mass / pre_mass) * 100.0,
    }


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/yield_loss_report.json"), "Output file not found"

    def test_values_correct(self):
        with open("/root/yield_loss_report.json", encoding="utf-8") as handle:
            submission = json.load(handle)

        expected = _ground_truth()
        required_keys = {
            "material_id",
            "pre_machining_volume_cm3",
            "post_machining_volume_cm3",
            "pre_machining_mass_g",
            "post_machining_mass_g",
            "removed_mass_g",
            "yield_percentage",
        }

        assert required_keys.issubset(submission.keys())
        assert submission["material_id"] == expected["material_id"]
        assert math.isclose(
            submission["pre_machining_volume_cm3"],
            expected["pre_machining_volume_cm3"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["post_machining_volume_cm3"],
            expected["post_machining_volume_cm3"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["pre_machining_mass_g"],
            expected["pre_machining_mass_g"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["post_machining_mass_g"],
            expected["post_machining_mass_g"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["removed_mass_g"],
            expected["removed_mass_g"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["yield_percentage"],
            expected["yield_percentage"],
            rel_tol=0.001,
        )
