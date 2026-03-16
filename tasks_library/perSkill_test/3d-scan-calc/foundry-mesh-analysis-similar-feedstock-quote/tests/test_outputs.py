import collections
import json
import math
import os
import re
import struct


class TestOutputs:
    OUTPUT_PATH = "/root/feedstock_quote.json"
    STL_PATH = "/root/foundry_scan.stl"
    DENSITY_PATH = "/root/alloy_density_table.md"
    COST_PATH = "/root/feedstock_cost_table.md"

    def test_file_exists(self):
        assert os.path.exists(self.OUTPUT_PATH), "Output file not found"

    def _load_density_table(self):
        density_table = {}
        with open(self.DENSITY_PATH, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line.startswith("|"):
                    continue
                cols = [col.strip() for col in line.strip("|").split("|")]
                if len(cols) < 3:
                    continue
                alloy_match = re.fullmatch(r"\d+", cols[0])
                density_match = re.fullmatch(r"\d+(?:\.\d+)?", cols[2])
                if alloy_match and density_match:
                    density_table[int(cols[0])] = float(cols[2])
        assert density_table, "Density table parsing failed"
        return density_table

    def _load_cost_table(self):
        cost_table = {}
        with open(self.COST_PATH, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line.startswith("|"):
                    continue
                cols = [col.strip() for col in line.strip("|").split("|")]
                if len(cols) < 3:
                    continue
                alloy_match = re.fullmatch(r"\d+", cols[0])
                usd_match = re.fullmatch(r"\d+(?:\.\d+)?", cols[1])
                multiplier_match = re.fullmatch(r"\d+(?:\.\d+)?", cols[2])
                if alloy_match and usd_match and multiplier_match:
                    cost_table[int(cols[0])] = (float(cols[1]), float(cols[2]))
        assert cost_table, "Cost table parsing failed"
        return cost_table

    def _parse_binary_stl(self):
        triangles = []
        with open(self.STL_PATH, "rb") as handle:
            handle.read(80)
            tri_count = struct.unpack("<I", handle.read(4))[0]
            for _ in range(tri_count):
                data = handle.read(50)
                floats = struct.unpack("<3f3f3f3f", data[:48])
                attr = struct.unpack("<H", data[48:50])[0]
                v1 = (floats[3], floats[4], floats[5])
                v2 = (floats[6], floats[7], floats[8])
                v3 = (floats[9], floats[10], floats[11])
                triangles.append((v1, v2, v3, attr))
        return triangles

    @staticmethod
    def _volume_of_component(component):
        total = 0.0
        for tri in component:
            v1, v2, v3 = tri[0], tri[1], tri[2]
            cp_x = v2[1] * v3[2] - v2[2] * v3[1]
            cp_y = v2[2] * v3[0] - v2[0] * v3[2]
            cp_z = v2[0] * v3[1] - v2[1] * v3[0]
            total += v1[0] * cp_x + v1[1] * cp_y + v1[2] * cp_z
        return abs(total) / 6.0

    def _connected_components(self, triangles):
        def quantize(vertex):
            return (round(vertex[0], 5), round(vertex[1], 5), round(vertex[2], 5))

        vertex_map = collections.defaultdict(list)
        for idx, tri in enumerate(triangles):
            for vertex in tri[:3]:
                vertex_map[quantize(vertex)].append(idx)

        visited = set()
        components = []

        for idx in range(len(triangles)):
            if idx in visited:
                continue

            queue = collections.deque([idx])
            visited.add(idx)
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

    def _ground_truth(self):
        density_table = self._load_density_table()
        cost_table = self._load_cost_table()
        triangles = self._parse_binary_stl()
        components = self._connected_components(triangles)
        assert components, "No components found in STL"

        main_component = max(components, key=self._volume_of_component)
        volume_cm3 = self._volume_of_component(main_component)
        alloy_code = main_component[0][3]

        assert alloy_code in density_table, f"Alloy code {alloy_code} missing from density table"
        assert alloy_code in cost_table, f"Alloy code {alloy_code} missing from cost table"

        density_g_per_cm3 = density_table[alloy_code]
        usd_per_kg, melt_loss_multiplier = cost_table[alloy_code]

        feedstock_mass_kg = volume_cm3 * density_g_per_cm3 / 1000.0
        feedstock_quote_usd = feedstock_mass_kg * usd_per_kg * melt_loss_multiplier

        return {
            "alloy_code": alloy_code,
            "main_component_volume_cm3": volume_cm3,
            "feedstock_mass_kg": feedstock_mass_kg,
            "feedstock_quote_usd": feedstock_quote_usd,
        }

    def test_values_correct(self):
        expected = self._ground_truth()

        with open(self.OUTPUT_PATH, "r", encoding="utf-8") as handle:
            submission = json.load(handle)

        required_keys = {
            "alloy_code",
            "main_component_volume_cm3",
            "feedstock_mass_kg",
            "feedstock_quote_usd",
        }
        assert required_keys.issubset(submission.keys()), "Missing required output keys"

        assert submission["alloy_code"] == expected["alloy_code"]

        assert math.isclose(
            submission["main_component_volume_cm3"],
            expected["main_component_volume_cm3"],
            rel_tol=0.001,
            abs_tol=1e-9,
        )
        assert math.isclose(
            submission["feedstock_mass_kg"],
            expected["feedstock_mass_kg"],
            rel_tol=0.001,
            abs_tol=1e-9,
        )
        assert math.isclose(
            submission["feedstock_quote_usd"],
            expected["feedstock_quote_usd"],
            rel_tol=0.001,
            abs_tol=1e-9,
        )
