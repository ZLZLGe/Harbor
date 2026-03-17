import collections
import json
import math
import os
import re


class TestOutputs:
    OUTPUT_PATH = "/root/silicone_pour_plan.json"
    STL_PATH = "/root/mold_insert_scan_ascii.stl"
    PROCESS_SHEET_PATH = "/root/silicone_process_sheet.md"

    def test_file_exists(self):
        assert os.path.exists(self.OUTPUT_PATH), "Output file not found"

    def _parse_process_sheet(self):
        values = {}

        with open(self.PROCESS_SHEET_PATH, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line.startswith("|"):
                    continue

                cols = [col.strip() for col in line.strip("|").split("|")]
                if len(cols) != 3:
                    continue
                if cols[0] == "Parameter" or cols[0] == "---":
                    continue

                name = cols[0].lower()
                number_match = re.search(r"-?\d+(?:\.\d+)?", cols[1])
                if not number_match:
                    continue
                values[name] = float(number_match.group(0))

        required = {"transfer factor", "reserve percent", "fixed loss"}
        assert required.issubset(values.keys()), "Process sheet parsing failed"
        return values

    def _parse_ascii_stl(self):
        triangles = []
        current_triangle = []

        with open(self.STL_PATH, "r", encoding="ascii") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue

                parts = line.split()
                if parts[0] == "vertex":
                    current_triangle.append((float(parts[1]), float(parts[2]), float(parts[3])))
                elif parts[0] == "endfacet":
                    assert len(current_triangle) == 3, "Malformed triangle in ASCII STL"
                    triangles.append(tuple(current_triangle))
                    current_triangle = []

        assert triangles, "No triangles parsed from ASCII STL"
        return triangles

    @staticmethod
    def _component_volume(component):
        total = 0.0
        for tri in component:
            v1, v2, v3 = tri
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
            for vertex in tri:
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
                for vertex in triangles[current]:
                    for neighbor in vertex_map[quantize(vertex)]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

            components.append([triangles[i] for i in component_indices])

        return components

    def _ground_truth(self):
        process_values = self._parse_process_sheet()
        triangles = self._parse_ascii_stl()
        components = self._connected_components(triangles)
        assert components, "No mesh components found"

        main_component = max(components, key=self._component_volume)
        main_component_volume_cm3 = self._component_volume(main_component)

        transfer_factor = process_values["transfer factor"]
        reserve_percent = process_values["reserve percent"] / 100.0
        fixed_loss_ml = process_values["fixed loss"]

        net_fill_volume_ml = main_component_volume_cm3 * transfer_factor
        reserve_volume_ml = net_fill_volume_ml * reserve_percent + fixed_loss_ml
        total_silicone_required_ml = net_fill_volume_ml + reserve_volume_ml

        return {
            "main_component_volume_cm3": main_component_volume_cm3,
            "net_fill_volume_ml": net_fill_volume_ml,
            "reserve_volume_ml": reserve_volume_ml,
            "total_silicone_required_ml": total_silicone_required_ml,
        }

    def test_values_correct(self):
        expected = self._ground_truth()

        with open(self.OUTPUT_PATH, "r", encoding="utf-8") as handle:
            submission = json.load(handle)

        required_keys = {
            "main_component_volume_cm3",
            "net_fill_volume_ml",
            "reserve_volume_ml",
            "total_silicone_required_ml",
        }
        assert required_keys.issubset(submission.keys()), "Missing required output keys"

        for key in required_keys:
            assert math.isclose(
                submission[key],
                expected[key],
                rel_tol=0.001,
                abs_tol=1e-9,
            ), f"{key} mismatch: expected {expected[key]}, got {submission[key]}"
