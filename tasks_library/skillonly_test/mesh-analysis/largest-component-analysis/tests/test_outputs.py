import collections
import json
import math
import os
import struct


def load_triangles(filepath: str):
    triangles = []
    with open(filepath, "rb") as handle:
        handle.read(80)
        count = struct.unpack("<I", handle.read(4))[0]
        for _ in range(count):
            data = handle.read(50)
            floats = struct.unpack("<3f3f3f3f", data[:48])
            attr = struct.unpack("<H", data[48:50])[0]
            v1 = (floats[3], floats[4], floats[5])
            v2 = (floats[6], floats[7], floats[8])
            v3 = (floats[9], floats[10], floats[11])
            triangles.append((v1, v2, v3, attr))
    return triangles


def quantize(vertex):
    return (round(vertex[0], 5), round(vertex[1], 5), round(vertex[2], 5))


def split_components(triangles):
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
    return components


def component_volume(component):
    total = 0.0
    for triangle in component:
        v1, v2, v3 = triangle[0], triangle[1], triangle[2]
        cp_x = v2[1] * v3[2] - v2[2] * v3[1]
        cp_y = v2[2] * v3[0] - v2[0] * v3[2]
        cp_z = v2[0] * v3[1] - v2[1] * v3[0]
        total += v1[0] * cp_x + v1[1] * cp_y + v1[2] * cp_z
    return abs(total) / 6.0


def expected_report():
    triangles = load_triangles("/root/scan_data.stl")
    components = split_components(triangles)
    volumes = [(component_volume(component), component) for component in components]
    largest_volume, largest_component = max(volumes, key=lambda item: item[0])
    return {
        "main_part_volume": largest_volume,
        "main_part_material_id": largest_component[0][3],
        "total_components": len(components),
    }


def main():
    output_path = "/root/outputs/largest_component_report.json"
    assert os.path.exists(output_path), "Output file not found"

    with open(output_path, "r", encoding="utf-8") as handle:
        result = json.load(handle)

    expected = expected_report()
    assert set(result.keys()) == set(expected.keys()), f"Unexpected keys: {sorted(result.keys())}"
    assert result["main_part_material_id"] == expected["main_part_material_id"]
    assert result["total_components"] == expected["total_components"]
    assert math.isclose(
        result["main_part_volume"],
        expected["main_part_volume"],
        rel_tol=1e-3,
    ), f"Volume mismatch: expected {expected['main_part_volume']}, got {result['main_part_volume']}"


if __name__ == "__main__":
    main()
