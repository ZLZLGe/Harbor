import collections
import csv
import json
import math
import os
import struct


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/production_quote.json"), "Output file not found"

    def _load_pricing(self):
        pricing = {}
        with open("/root/material_pricing.csv", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                pricing[int(row["material_id"])] = {
                    "density_g_cm3": float(row["density_g_cm3"]),
                    "powder_price_usd_per_kg": float(row["powder_price_usd_per_kg"]),
                }
        return pricing

    def _largest_component_quote(self):
        triangles = []
        with open("/root/powder_bed_scan.stl", "rb") as handle:
            handle.read(80)
            count = struct.unpack("<I", handle.read(4))[0]
            for _ in range(count):
                data = handle.read(50)
                floats = struct.unpack("<12f", data[:48])
                attr = struct.unpack("<H", data[48:50])[0]
                v1 = (floats[3], floats[4], floats[5])
                v2 = (floats[6], floats[7], floats[8])
                v3 = (floats[9], floats[10], floats[11])
                triangles.append((v1, v2, v3, attr))

        def quantize(vertex):
            return (round(vertex[0], 5), round(vertex[1], 5), round(vertex[2], 5))

        vertex_map = collections.defaultdict(list)
        for index, triangle in enumerate(triangles):
            for vertex in triangle[:3]:
                vertex_map[quantize(vertex)].append(index)

        visited = set()
        components = []
        for start in range(len(triangles)):
            if start in visited:
                continue

            queue = collections.deque([start])
            visited.add(start)
            component = []

            while queue:
                current = queue.popleft()
                component.append(triangles[current])
                for vertex in triangles[current][:3]:
                    for neighbor in vertex_map[quantize(vertex)]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

            components.append(component)

        def volume(component):
            total = 0.0
            for triangle in component:
                v1, v2, v3 = triangle[:3]
                cp_x = v2[1] * v3[2] - v2[2] * v3[1]
                cp_y = v2[2] * v3[0] - v2[0] * v3[2]
                cp_z = v2[0] * v3[1] - v2[1] * v3[0]
                total += v1[0] * cp_x + v1[1] * cp_y + v1[2] * cp_z
            return abs(total) / 6.0

        largest = max(components, key=volume)
        part_volume_cm3 = volume(largest)
        material_id = largest[0][3]

        pricing = self._load_pricing()
        material = pricing[material_id]
        part_mass_g = part_volume_cm3 * material["density_g_cm3"]
        material_cost_usd = (part_mass_g / 1000.0) * material["powder_price_usd_per_kg"]

        return {
            "material_id": material_id,
            "part_volume_cm3": part_volume_cm3,
            "part_mass_g": part_mass_g,
            "powder_unit_price_usd_per_kg": material["powder_price_usd_per_kg"],
            "material_cost_usd": material_cost_usd,
        }

    def test_values_correct(self):
        expected = self._largest_component_quote()

        with open("/root/production_quote.json") as handle:
            submission = json.load(handle)

        required_keys = {
            "material_id",
            "part_volume_cm3",
            "part_mass_g",
            "powder_unit_price_usd_per_kg",
            "material_cost_usd",
        }
        assert required_keys.issubset(submission.keys())

        assert submission["material_id"] == expected["material_id"]
        assert math.isclose(
            submission["part_volume_cm3"],
            expected["part_volume_cm3"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["part_mass_g"],
            expected["part_mass_g"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["powder_unit_price_usd_per_kg"],
            expected["powder_unit_price_usd_per_kg"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["material_cost_usd"],
            expected["material_cost_usd"],
            rel_tol=0.001,
        )
