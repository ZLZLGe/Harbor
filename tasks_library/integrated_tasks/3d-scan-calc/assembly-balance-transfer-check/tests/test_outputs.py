import collections
import json
import math
import os
import re
import struct


def parse_binary_stl(path):
    triangles = []
    with open(path, "rb") as f:
        f.read(80)
        count = struct.unpack("<I", f.read(4))[0]
        for _ in range(count):
            data = f.read(50)
            values = struct.unpack("<3f3f3f3f", data[:48])
            material_id = struct.unpack("<H", data[48:50])[0]
            v1 = (values[3], values[4], values[5])
            v2 = (values[6], values[7], values[8])
            v3 = (values[9], values[10], values[11])
            triangles.append((v1, v2, v3, material_id))
    return triangles


def split_components(triangles):
    def quantize(vertex):
        return (round(vertex[0], 5), round(vertex[1], 5), round(vertex[2], 5))

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

        components.append([triangles[i] for i in component_indices])

    return components


def volume_and_centroid(triangles):
    signed_volume = 0.0
    centroid_x = 0.0
    centroid_y = 0.0
    centroid_z = 0.0

    for triangle in triangles:
        v1, v2, v3 = triangle[:3]
        cross_x = v2[1] * v3[2] - v2[2] * v3[1]
        cross_y = v2[2] * v3[0] - v2[0] * v3[2]
        cross_z = v2[0] * v3[1] - v2[1] * v3[0]
        signed_tetra_six = v1[0] * cross_x + v1[1] * cross_y + v1[2] * cross_z

        signed_volume += signed_tetra_six
        centroid_x += (v1[0] + v2[0] + v3[0]) * signed_tetra_six
        centroid_y += (v1[1] + v2[1] + v3[1]) * signed_tetra_six
        centroid_z += (v1[2] + v2[2] + v3[2]) * signed_tetra_six

    signed_volume /= 6.0
    centroid = {
        "x": centroid_x / (24.0 * signed_volume),
        "y": centroid_y / (24.0 * signed_volume),
        "z": centroid_z / (24.0 * signed_volume),
    }
    return abs(signed_volume), centroid


def parse_density_table(path):
    densities = {}
    pattern = re.compile(r"\|\s*\*\*(\d+)\*\*\s*\|[^|]*\|\s*([0-9.]+)\s*\|")
    with open(path) as f:
        for line in f:
            match = pattern.search(line)
            if match:
                densities[int(match.group(1))] = float(match.group(2))
    return densities


def parse_requirements(path):
    rules = {}
    with open(path) as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line.startswith("|"):
                continue
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) != 3 or parts[0] in {"Rule", ":---"}:
                continue
            rules[parts[0]] = float(parts[1])
    return {
        "min_volume": rules["Minimum Assembly Component Volume (cm^3)"],
        "x_min": rules["Footprint X Min (cm)"],
        "x_max": rules["Footprint X Max (cm)"],
        "y_min": rules["Footprint Y Min (cm)"],
        "y_max": rules["Footprint Y Max (cm)"],
    }


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/assembly_balance.json"), "Output file not found"

    def _ground_truth(self):
        triangles = parse_binary_stl("/root/assembly_scan.stl")
        components = split_components(triangles)
        densities = parse_density_table("/root/material_density_table.md")
        requirements = parse_requirements("/root/assembly_requirements.md")

        meaningful = []
        for component in components:
            volume_cm3, centroid = volume_and_centroid(component)
            if volume_cm3 < requirements["min_volume"]:
                continue
            material_id = component[0][3]
            meaningful.append(
                {
                    "material_id": material_id,
                    "volume_cm3": volume_cm3,
                    "mass_g": volume_cm3 * densities[material_id],
                    "centroid_cm": centroid,
                }
            )

        meaningful.sort(key=lambda item: (-item["volume_cm3"], item["material_id"]))
        total_mass_g = sum(item["mass_g"] for item in meaningful)
        assembly_center = {
            axis: sum(item["mass_g"] * item["centroid_cm"][axis] for item in meaningful) / total_mass_g
            for axis in ("x", "y", "z")
        }
        inside = (
            requirements["x_min"] <= assembly_center["x"] <= requirements["x_max"]
            and requirements["y_min"] <= assembly_center["y"] <= requirements["y_max"]
        )

        return {
            "meaningful_component_count": len(meaningful),
            "components": meaningful,
            "total_mass_g": total_mass_g,
            "assembly_center_of_mass_cm": assembly_center,
            "balance_result": "pass" if inside else "fail",
        }

    def test_values_correct(self):
        expected = self._ground_truth()

        with open("/root/assembly_balance.json") as f:
            submission = json.load(f)

        assert set(submission) == {
            "meaningful_component_count",
            "components",
            "total_mass_g",
            "assembly_center_of_mass_cm",
            "balance_result",
        }
        assert submission["meaningful_component_count"] == expected["meaningful_component_count"]
        assert submission["balance_result"] == expected["balance_result"]

        assert isinstance(submission["components"], list)
        assert len(submission["components"]) == expected["meaningful_component_count"]

        for actual, reference in zip(submission["components"], expected["components"]):
            assert set(actual) == {"material_id", "volume_cm3", "mass_g", "centroid_cm"}
            assert actual["material_id"] == reference["material_id"]
            assert math.isclose(actual["volume_cm3"], reference["volume_cm3"], rel_tol=0.001)
            assert math.isclose(actual["mass_g"], reference["mass_g"], rel_tol=0.001)
            assert set(actual["centroid_cm"]) == {"x", "y", "z"}
            for axis in ("x", "y", "z"):
                assert math.isclose(
                    actual["centroid_cm"][axis],
                    reference["centroid_cm"][axis],
                    rel_tol=0.001,
                    abs_tol=1e-6,
                )

        assert math.isclose(submission["total_mass_g"], expected["total_mass_g"], rel_tol=0.001)
        assert set(submission["assembly_center_of_mass_cm"]) == {"x", "y", "z"}
        for axis in ("x", "y", "z"):
            assert math.isclose(
                submission["assembly_center_of_mass_cm"][axis],
                expected["assembly_center_of_mass_cm"][axis],
                rel_tol=0.001,
                abs_tol=1e-6,
            )
