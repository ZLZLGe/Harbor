import collections
import json
import math
import re
import struct
import unittest
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]
INPUT_STL = TASK_ROOT / "environment" / "scan_input.stl"
PRICE_TABLE = TASK_ROOT / "environment" / "material_price_table.md"
OUTPUT_PATH = TASK_ROOT / "output" / "pricing_report.json"


def load_price_table(path: Path) -> dict[int, float]:
    mapping: dict[int, float] = {}
    pattern = re.compile(r"\|\s*\*\*(\d+)\*\*\s*\|[^|]*\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            mapping[int(match.group(1))] = float(match.group(2))
    return mapping


def parse_binary_stl(filepath: Path):
    triangles = []
    with filepath.open("rb") as handle:
        handle.read(80)
        count = struct.unpack("<I", handle.read(4))[0]
        for _ in range(count):
            data = handle.read(50)
            floats = struct.unpack("<3f3f3f3f", data[:48])
            attribute = struct.unpack("<H", data[48:50])[0]
            vertex_1 = (floats[3], floats[4], floats[5])
            vertex_2 = (floats[6], floats[7], floats[8])
            vertex_3 = (floats[9], floats[10], floats[11])
            triangles.append((vertex_1, vertex_2, vertex_3, attribute))
    return triangles


def split_components(triangles):
    def quantize(vertex):
        return (round(vertex[0], 4), round(vertex[1], 4), round(vertex[2], 4))

    vertex_map = collections.defaultdict(list)
    for index, triangle in enumerate(triangles):
        for vertex in triangle[:3]:
            vertex_map[quantize(vertex)].append(index)

    visited = set()
    components = []

    for start_index in range(len(triangles)):
        if start_index in visited:
            continue

        queue = collections.deque([start_index])
        visited.add(start_index)
        component_indices = []

        while queue:
            current_index = queue.popleft()
            component_indices.append(current_index)
            for vertex in triangles[current_index][:3]:
                for neighbor_index in vertex_map[quantize(vertex)]:
                    if neighbor_index not in visited:
                        visited.add(neighbor_index)
                        queue.append(neighbor_index)

        components.append([triangles[index] for index in component_indices])

    return components


def calc_volume(triangles):
    total = 0.0
    for triangle in triangles:
        vertex_1, vertex_2, vertex_3 = triangle[0], triangle[1], triangle[2]
        cp_x = vertex_2[1] * vertex_3[2] - vertex_2[2] * vertex_3[1]
        cp_y = vertex_2[2] * vertex_3[0] - vertex_2[0] * vertex_3[2]
        cp_z = vertex_2[0] * vertex_3[1] - vertex_2[1] * vertex_3[0]
        total += vertex_1[0] * cp_x + vertex_1[1] * cp_y + vertex_1[2] * cp_z
    return abs(total) / 6.0


def compute_ground_truth():
    triangles = parse_binary_stl(INPUT_STL)
    components = split_components(triangles)
    price_table = load_price_table(PRICE_TABLE)

    reports = []
    for component in components:
        volume = calc_volume(component)
        material_id = component[0][3]
        estimated_cost = volume * price_table[material_id]
        reports.append((estimated_cost, material_id, volume))

    reports.sort(key=lambda item: item[2], reverse=True)
    return reports[0]


class TestOutputs(unittest.TestCase):
    def test_file_exists(self):
        self.assertTrue(OUTPUT_PATH.exists(), "Output file not found")

    def test_output_values(self):
        expected_cost, expected_material_id, _ = compute_ground_truth()
        submission = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

        self.assertIn("main_part_estimated_cost", submission)
        self.assertIn("material_id", submission)
        self.assertEqual(submission["material_id"], expected_material_id)
        self.assertTrue(
            math.isclose(submission["main_part_estimated_cost"], expected_cost, rel_tol=0.001),
            f"Expected ~{expected_cost:.6f}, got {submission['main_part_estimated_cost']:.6f}",
        )


if __name__ == "__main__":
    unittest.main()
