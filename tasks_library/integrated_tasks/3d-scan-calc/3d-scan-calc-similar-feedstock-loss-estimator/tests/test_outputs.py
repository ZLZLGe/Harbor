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


def _load_waste_factors():
    factors = {}
    with open("/root/feedstock_waste_factors.md", encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"\|\s*\**(\d+)\**\s*\|\s*([0-9.]+)\s*\|", line)
            if match:
                factors[int(match.group(1))] = float(match.group(2))
    return factors


def _parse_binary_stl():
    triangles = []
    with open("/root/scan_data.stl", "rb") as handle:
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


def _ground_truth():
    triangles = _parse_binary_stl()
    components = _connected_components(triangles)
    densities = _load_density_table()
    factors = _load_waste_factors()

    largest_component = max(components, key=_volume)
    component_volume = _volume(largest_component)
    material_id = largest_component[0][3]
    density = densities[material_id]
    waste_factor = factors[material_id]
    net_part_mass = component_volume * density
    required_feedstock_mass = net_part_mass / (1.0 - waste_factor)
    estimated_waste_mass = required_feedstock_mass - net_part_mass

    return {
        "material_id": material_id,
        "net_part_mass": net_part_mass,
        "waste_factor": waste_factor,
        "required_feedstock_mass": required_feedstock_mass,
        "estimated_waste_mass": estimated_waste_mass,
    }


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/feedstock_plan.json"), "Output file not found"

    def test_values_correct(self):
        with open("/root/feedstock_plan.json", encoding="utf-8") as handle:
            submission = json.load(handle)

        expected = _ground_truth()
        required_keys = {
            "material_id",
            "net_part_mass",
            "waste_factor",
            "required_feedstock_mass",
            "estimated_waste_mass",
        }

        assert required_keys.issubset(submission.keys())
        assert submission["material_id"] == expected["material_id"]
        assert math.isclose(submission["waste_factor"], expected["waste_factor"], rel_tol=1e-9)
        assert math.isclose(submission["net_part_mass"], expected["net_part_mass"], rel_tol=0.001)
        assert math.isclose(
            submission["required_feedstock_mass"],
            expected["required_feedstock_mass"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["estimated_waste_mass"],
            expected["estimated_waste_mass"],
            rel_tol=0.001,
        )
