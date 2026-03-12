import collections
import json
import math
import os
import struct


def triangle_area(triangle):
    v1, v2, v3 = triangle[:3]
    ax = v2[0] - v1[0]
    ay = v2[1] - v1[1]
    az = v2[2] - v1[2]
    bx = v3[0] - v1[0]
    by = v3[1] - v1[1]
    bz = v3[2] - v1[2]
    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


def parse_stl(filepath):
    triangles = []
    with open(filepath, "rb") as f:
        f.read(80)
        count = struct.unpack("<I", f.read(4))[0]
        for _ in range(count):
            data = f.read(50)
            floats = struct.unpack("<3f3f3f3f", data[:48])
            attr = struct.unpack("<H", data[48:50])[0]
            v1 = (floats[3], floats[4], floats[5])
            v2 = (floats[6], floats[7], floats[8])
            v3 = (floats[9], floats[10], floats[11])
            triangles.append((v1, v2, v3, attr))
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


def component_volume(triangles):
    total = 0.0
    for triangle in triangles:
        v1, v2, v3 = triangle[:3]
        cp_x = v2[1] * v3[2] - v2[2] * v3[1]
        cp_y = v2[2] * v3[0] - v2[0] * v3[2]
        cp_z = v2[0] * v3[1] - v2[1] * v3[0]
        total += v1[0] * cp_x + v1[1] * cp_y + v1[2] * cp_z
    return abs(total) / 6.0


def component_surface_area(triangles):
    return sum(triangle_area(triangle) for triangle in triangles)


def parse_process_table(path):
    recipes = {}
    with open(path) as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line.startswith("|"):
                continue
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) != 6 or parts[0] in {"Recipe ID", "---"}:
                continue
            recipe_id = int(parts[0])
            recipes[recipe_id] = {
                "dry_film_thickness_mm": float(parts[2]),
                "cured_density_g_per_cm3": float(parts[3]),
                "transfer_efficiency": float(parts[4]),
                "material_cost_usd_per_kg": float(parts[5]),
            }
    return recipes


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/coating_estimate.json"), "Output file not found"

    def _ground_truth(self):
        triangles = parse_stl("/root/scan_data.stl")
        components = split_components(triangles)
        largest_component = max(components, key=component_volume)

        recipe_id = largest_component[0][3]
        surface_area_cm2 = component_surface_area(largest_component)

        recipes = parse_process_table("/root/coating_process_table.md")
        recipe = recipes[recipe_id]
        dry_volume_cm3 = surface_area_cm2 * (recipe["dry_film_thickness_mm"] / 10.0)
        coating_mass_g = dry_volume_cm3 * recipe["cured_density_g_per_cm3"] / recipe["transfer_efficiency"]
        coating_cost_usd = coating_mass_g / 1000.0 * recipe["material_cost_usd_per_kg"]

        return {
            "recipe_id": recipe_id,
            "surface_area_cm2": surface_area_cm2,
            "coating_mass_g": coating_mass_g,
            "coating_cost_usd": coating_cost_usd,
        }

    def test_values_correct(self):
        expected = self._ground_truth()

        with open("/root/coating_estimate.json") as f:
            submission = json.load(f)

        assert set(submission) == {
            "recipe_id",
            "surface_area_cm2",
            "coating_mass_g",
            "coating_cost_usd",
        }
        assert submission["recipe_id"] == expected["recipe_id"]
        assert math.isclose(
            submission["surface_area_cm2"],
            expected["surface_area_cm2"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["coating_mass_g"],
            expected["coating_mass_g"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["coating_cost_usd"],
            expected["coating_cost_usd"],
            rel_tol=0.001,
        )
