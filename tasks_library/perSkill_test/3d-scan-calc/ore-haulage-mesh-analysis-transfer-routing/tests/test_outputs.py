import collections
import csv
import json
import math
import os
import struct
import tomllib


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/ore_manifest.json"), "Output file not found"

    def _load_catalog(self):
        catalog = {}
        with open("/root/ore_type_catalog.csv", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                catalog[int(row["ore_type_id"])] = {
                    "bulk_density_t_per_m3": float(row["bulk_density_t_per_m3"]),
                    "fe_grade_pct": float(row["fe_grade_pct"]),
                    "silica_pct": float(row["silica_pct"]),
                }
        return catalog

    def _expected_manifest(self):
        triangles = []
        with open("/root/conveyor_ore_scan.stl", "rb") as handle:
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

        def volume_cm3(component):
            total = 0.0
            for triangle in component:
                v1, v2, v3 = triangle[:3]
                cp_x = v2[1] * v3[2] - v2[2] * v3[1]
                cp_y = v2[2] * v3[0] - v2[0] * v3[2]
                cp_z = v2[0] * v3[1] - v2[1] * v3[0]
                total += v1[0] * cp_x + v1[1] * cp_y + v1[2] * cp_z
            return abs(total) / 6.0

        largest = max(components, key=volume_cm3)
        ore_type_id = largest[0][3]
        main_ore_volume_m3 = volume_cm3(largest) / 1_000_000.0

        catalog = self._load_catalog()
        ore = catalog[ore_type_id]
        estimated_mass_tonnes = main_ore_volume_m3 * ore["bulk_density_t_per_m3"]

        with open("/root/routing_rules.toml", "rb") as handle:
            rules = tomllib.load(handle)

        selected_route = None
        for route in rules["routes"]:
            if (
                ore["fe_grade_pct"] >= route["min_fe_grade_pct"]
                and ore["silica_pct"] <= route["max_silica_pct"]
                and estimated_mass_tonnes <= route["max_mass_tonnes"]
            ):
                selected_route = route
                break

        assert selected_route is not None

        return {
            "ore_type_id": ore_type_id,
            "main_ore_volume_m3": main_ore_volume_m3,
            "estimated_mass_tonnes": estimated_mass_tonnes,
            "dispatch_line": selected_route["dispatch_line"],
            "diversion_gate": selected_route["diversion_gate"],
            "requires_breaker": estimated_mass_tonnes >= rules["breaker"]["threshold_tonnes"],
        }

    def test_values_correct(self):
        expected = self._expected_manifest()

        with open("/root/ore_manifest.json") as handle:
            submission = json.load(handle)

        required_keys = {
            "ore_type_id",
            "main_ore_volume_m3",
            "estimated_mass_tonnes",
            "dispatch_line",
            "diversion_gate",
            "requires_breaker",
        }
        assert required_keys.issubset(submission.keys())

        assert submission["ore_type_id"] == expected["ore_type_id"]
        assert submission["dispatch_line"] == expected["dispatch_line"]
        assert submission["diversion_gate"] == expected["diversion_gate"]
        assert submission["requires_breaker"] == expected["requires_breaker"]
        assert math.isclose(
            submission["main_ore_volume_m3"],
            expected["main_ore_volume_m3"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["estimated_mass_tonnes"],
            expected["estimated_mass_tonnes"],
            rel_tol=0.001,
        )
        assert submission["estimated_mass_tonnes"] > 0
