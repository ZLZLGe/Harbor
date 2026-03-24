import collections
import json
import math
import os
import struct
import tomllib


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/lift_plan.json"), "Output file not found"

    def _load_alloys(self):
        with open("/root/alloy_registry.json") as handle:
            payload = json.load(handle)
        return {entry["alloy_id"]: entry for entry in payload["alloys"]}

    def _largest_component_metrics(self):
        triangles = []
        with open("/root/subsea_recovery_scan.stl", "rb") as handle:
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
        alloy_id = largest[0][3]
        main_body_volume_m3 = volume_cm3(largest) / 1_000_000.0

        alloys = self._load_alloys()
        density_kg_m3 = alloys[alloy_id]["density_kg_m3"]

        with open("/root/recovery_factors.toml", "rb") as handle:
            factors = tomllib.load(handle)

        gravity = factors["hydrostatics"]["gravity_m_s2"]
        seawater_density = factors["hydrostatics"]["seawater_density_kg_m3"]
        dynamic_factor = factors["rigging"]["dynamic_amplification_factor"]

        dry_weight_kN = main_body_volume_m3 * density_kg_m3 * gravity / 1000.0
        underwater_lift_load_kN = (
            main_body_volume_m3
            * (density_kg_m3 - seawater_density)
            * gravity
            / 1000.0
            * dynamic_factor
        )

        return {
            "alloy_id": alloy_id,
            "main_body_volume_m3": main_body_volume_m3,
            "dry_weight_kN": dry_weight_kN,
            "underwater_lift_load_kN": underwater_lift_load_kN,
        }

    def test_values_correct(self):
        expected = self._largest_component_metrics()

        with open("/root/lift_plan.json") as handle:
            submission = json.load(handle)

        required_keys = {
            "alloy_id",
            "main_body_volume_m3",
            "dry_weight_kN",
            "underwater_lift_load_kN",
        }
        assert required_keys.issubset(submission.keys())
        assert submission["alloy_id"] == expected["alloy_id"]
        assert math.isclose(
            submission["main_body_volume_m3"],
            expected["main_body_volume_m3"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["dry_weight_kN"],
            expected["dry_weight_kN"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["underwater_lift_load_kN"],
            expected["underwater_lift_load_kN"],
            rel_tol=0.001,
        )
        assert submission["underwater_lift_load_kN"] < submission["dry_weight_kN"]
