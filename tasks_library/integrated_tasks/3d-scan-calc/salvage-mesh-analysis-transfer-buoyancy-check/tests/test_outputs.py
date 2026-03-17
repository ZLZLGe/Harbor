import collections
import json
import math
import os
import re
import struct


class TestOutputs:
    OUTPUT_PATH = "/root/buoyancy_report.json"
    STL_PATH = "/root/recovered_artifact_scan.stl"
    REFERENCE_PATH = "/root/salvage_density_reference.md"

    def test_file_exists(self):
        assert os.path.exists(self.OUTPUT_PATH), "Output file not found"

    def _load_reference_tables(self):
        material_density = {}
        fluid_density = {}

        with open(self.REFERENCE_PATH, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line.startswith("|"):
                    continue

                cols = [col.strip() for col in line.strip("|").split("|")]
                if len(cols) < 2:
                    continue

                if len(cols) >= 3 and re.fullmatch(r"\d+", cols[0]) and re.fullmatch(r"\d+(?:\.\d+)?", cols[2]):
                    material_density[int(cols[0])] = float(cols[2])
                    continue

                if cols[0] and re.fullmatch(r"\d+(?:\.\d+)?", cols[1]):
                    fluid_density[cols[0].lower()] = float(cols[1])

        assert material_density, "Material density parsing failed"
        assert "seawater" in fluid_density, "Seawater density parsing failed"
        return material_density, fluid_density

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
    def _component_volume(component):
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
        material_density, fluid_density = self._load_reference_tables()
        triangles = self._parse_binary_stl()
        components = self._connected_components(triangles)
        assert components, "No mesh components found"

        main_component = max(components, key=self._component_volume)
        volume_cm3 = self._component_volume(main_component)
        material_id = main_component[0][3]

        assert material_id in material_density, f"Material ID {material_id} missing from reference"

        artifact_density = material_density[material_id]
        seawater_density = fluid_density["seawater"]
        artifact_mass = volume_cm3 * artifact_density
        displaced_seawater_mass = volume_cm3 * seawater_density
        buoyancy_margin = displaced_seawater_mass - artifact_mass
        seawater_result = "floats" if buoyancy_margin > 0 else "sinks"

        return {
            "material_id": material_id,
            "main_component_volume_cm3": volume_cm3,
            "artifact_density_g_cm3": artifact_density,
            "seawater_density_g_cm3": seawater_density,
            "artifact_mass_g": artifact_mass,
            "displaced_seawater_mass_g": displaced_seawater_mass,
            "buoyancy_margin_g": buoyancy_margin,
            "seawater_result": seawater_result,
        }

    def test_values_correct(self):
        expected = self._ground_truth()

        with open(self.OUTPUT_PATH, "r", encoding="utf-8") as handle:
            submission = json.load(handle)

        required_keys = {
            "material_id",
            "main_component_volume_cm3",
            "artifact_density_g_cm3",
            "seawater_density_g_cm3",
            "artifact_mass_g",
            "displaced_seawater_mass_g",
            "buoyancy_margin_g",
            "seawater_result",
        }
        assert required_keys.issubset(submission.keys()), "Missing required output keys"

        assert submission["material_id"] == expected["material_id"]
        assert submission["seawater_result"] == expected["seawater_result"]

        for key in (
            "main_component_volume_cm3",
            "artifact_density_g_cm3",
            "seawater_density_g_cm3",
            "artifact_mass_g",
            "displaced_seawater_mass_g",
            "buoyancy_margin_g",
        ):
            assert math.isclose(
                submission[key],
                expected[key],
                rel_tol=0.001,
                abs_tol=1e-9,
            ), f"{key} mismatch: expected {expected[key]}, got {submission[key]}"
