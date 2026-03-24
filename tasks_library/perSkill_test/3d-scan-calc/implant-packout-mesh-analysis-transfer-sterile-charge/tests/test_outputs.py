import collections
import csv
import json
import math
import os
import struct
import tomllib


class TestOutputs:
    def test_file_exists(self):
        assert os.path.exists("/root/sterile_packout.json"), "Output file not found"

    def _load_profiles(self):
        profiles = {}
        with open("/root/implant_material_profiles.tsv", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                profiles[int(row["material_id"])] = {
                    "fill_multiplier": float(row["fill_multiplier"]),
                    "base_handling_fee_usd": float(row["base_handling_fee_usd"]),
                }
        return profiles

    def _expected_packout(self):
        triangles = []
        with open("/root/implant_segment.stl", "rb") as handle:
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

        def volume_mm3(component):
            total = 0.0
            for triangle in component:
                v1, v2, v3 = triangle[:3]
                cp_x = v2[1] * v3[2] - v2[2] * v3[1]
                cp_y = v2[2] * v3[0] - v2[0] * v3[2]
                cp_z = v2[0] * v3[1] - v2[1] * v3[0]
                total += v1[0] * cp_x + v1[1] * cp_y + v1[2] * cp_z
            return abs(total) / 6.0

        largest = max(components, key=volume_mm3)
        material_id = largest[0][3]
        implant_volume_cm3 = volume_mm3(largest) / 1000.0

        profiles = self._load_profiles()
        profile = profiles[material_id]

        with open("/root/sterile_packout_policy.toml", "rb") as handle:
            policy = tomllib.load(handle)

        sterile_fill_volume_ml = (
            implant_volume_cm3 * profile["fill_multiplier"] + policy["fill"]["baseline_fill_ml"]
        )

        pouch_size = "large"
        for name, capacity in sorted(policy["pouch_capacity_ml"].items(), key=lambda item: item[1]):
            if sterile_fill_volume_ml <= capacity:
                pouch_size = name
                break

        absorbent_pad_count = math.ceil(sterile_fill_volume_ml / policy["pads"]["ml_per_pad"])
        sterile_packout_charge_usd = profile["base_handling_fee_usd"] + (
            math.ceil(sterile_fill_volume_ml / policy["pricing"]["charge_step_ml"])
            * policy["pricing"]["charge_per_step_usd"]
        )

        return {
            "material_id": material_id,
            "implant_volume_cm3": implant_volume_cm3,
            "sterile_fill_volume_ml": sterile_fill_volume_ml,
            "pouch_size": pouch_size,
            "absorbent_pad_count": absorbent_pad_count,
            "sterile_packout_charge_usd": sterile_packout_charge_usd,
        }

    def test_values_correct(self):
        expected = self._expected_packout()

        with open("/root/sterile_packout.json") as handle:
            submission = json.load(handle)

        required_keys = {
            "material_id",
            "implant_volume_cm3",
            "sterile_fill_volume_ml",
            "pouch_size",
            "absorbent_pad_count",
            "sterile_packout_charge_usd",
        }
        assert required_keys.issubset(submission.keys())

        assert submission["material_id"] == expected["material_id"]
        assert submission["pouch_size"] == expected["pouch_size"]
        assert submission["absorbent_pad_count"] == expected["absorbent_pad_count"]
        assert math.isclose(
            submission["implant_volume_cm3"],
            expected["implant_volume_cm3"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["sterile_fill_volume_ml"],
            expected["sterile_fill_volume_ml"],
            rel_tol=0.001,
        )
        assert math.isclose(
            submission["sterile_packout_charge_usd"],
            expected["sterile_packout_charge_usd"],
            rel_tol=0.001,
        )
        assert submission["sterile_fill_volume_ml"] > submission["implant_volume_cm3"]
