import collections
import json
import math
import os
import re
import struct


class TestOutputs:
    OUTPUT_PATH = "/root/fragment_audit.json"
    STL_PATH = "/root/fragment_audit_scan.stl"
    POLICY_PATH = "/root/fragment_cleanliness_policy.md"

    def test_file_exists(self):
        assert os.path.exists(self.OUTPUT_PATH), "Output file not found"

    def _load_threshold(self):
        with open(self.POLICY_PATH, "r", encoding="utf-8") as handle:
            text = handle.read()

        match = re.search(r"Max debris-volume ratio\s*\|\s*([0-9]+(?:\.[0-9]+)?)%", text)
        assert match, "Failed to parse cleanliness threshold"
        return float(match.group(1)) / 100.0

    def _parse_binary_stl(self):
        triangles = []

        with open(self.STL_PATH, "rb") as handle:
            handle.read(80)
            count = struct.unpack("<I", handle.read(4))[0]

            for _ in range(count):
                record = handle.read(50)
                floats = struct.unpack("<3f3f3f3f", record[:48])
                vertices = (
                    (floats[3], floats[4], floats[5]),
                    (floats[6], floats[7], floats[8]),
                    (floats[9], floats[10], floats[11]),
                )
                triangles.append(vertices)

        assert triangles, "No triangles parsed from binary STL"
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
        triangles = self._parse_binary_stl()
        components = self._connected_components(triangles)
        assert components, "No connected components found"

        component_volumes = [self._component_volume(component) for component in components]
        component_count = len(component_volumes)
        fragment_count = component_count - 1
        main_assembly_volume_cm3 = max(component_volumes)
        total_volume_cm3 = sum(component_volumes)
        debris_volume_cm3 = total_volume_cm3 - main_assembly_volume_cm3
        debris_volume_ratio = debris_volume_cm3 / total_volume_cm3
        threshold = self._load_threshold()

        return {
            "component_count": component_count,
            "fragment_count": fragment_count,
            "fragment_count_ratio": fragment_count / component_count,
            "main_assembly_volume_cm3": main_assembly_volume_cm3,
            "debris_volume_cm3": debris_volume_cm3,
            "debris_volume_ratio": debris_volume_ratio,
            "cleanliness_threshold": threshold,
            "passes_cleanliness_threshold": debris_volume_ratio <= threshold,
        }

    def test_values_correct(self):
        expected = self._ground_truth()

        with open(self.OUTPUT_PATH, "r", encoding="utf-8") as handle:
            submission = json.load(handle)

        required_keys = {
            "component_count",
            "fragment_count",
            "fragment_count_ratio",
            "main_assembly_volume_cm3",
            "debris_volume_cm3",
            "debris_volume_ratio",
            "cleanliness_threshold",
            "passes_cleanliness_threshold",
        }
        assert required_keys.issubset(submission.keys()), "Missing required output keys"

        for key in {
            "component_count",
            "fragment_count",
            "passes_cleanliness_threshold",
        }:
            assert submission[key] == expected[key], f"{key} mismatch: expected {expected[key]}, got {submission[key]}"

        for key in required_keys.difference({"component_count", "fragment_count", "passes_cleanliness_threshold"}):
            assert math.isclose(
                submission[key],
                expected[key],
                rel_tol=0.001,
                abs_tol=1e-9,
            ), f"{key} mismatch: expected {expected[key]}, got {submission[key]}"
