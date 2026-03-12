#!/bin/bash
set -e

cat <<'EOF' > /root/solve_task.py
import collections
import json
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


def main():
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
        mass_g = volume_cm3 * densities[material_id]
        meaningful.append(
            {
                "material_id": material_id,
                "volume_cm3": volume_cm3,
                "mass_g": mass_g,
                "centroid_cm": centroid,
            }
        )

    meaningful.sort(key=lambda item: (-item["volume_cm3"], item["material_id"]))

    total_mass_g = sum(item["mass_g"] for item in meaningful)
    assembly_center_of_mass_cm = {
        axis: sum(item["mass_g"] * item["centroid_cm"][axis] for item in meaningful) / total_mass_g
        for axis in ("x", "y", "z")
    }

    inside = (
        requirements["x_min"] <= assembly_center_of_mass_cm["x"] <= requirements["x_max"]
        and requirements["y_min"] <= assembly_center_of_mass_cm["y"] <= requirements["y_max"]
    )

    result = {
        "meaningful_component_count": len(meaningful),
        "components": meaningful,
        "total_mass_g": total_mass_g,
        "assembly_center_of_mass_cm": assembly_center_of_mass_cm,
        "balance_result": "pass" if inside else "fail",
    }

    with open("/root/assembly_balance.json", "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
EOF

python3 /root/solve_task.py
