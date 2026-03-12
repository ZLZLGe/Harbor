import collections
import os
import struct


class MeshAnalyzer:
    def __init__(self, filepath):
        self.filepath = filepath
        self.triangles = []
        self._parse()

    def _parse(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"{self.filepath} not found.")

        self._parse_binary()

    def _parse_binary(self):
        with open(self.filepath, "rb") as handle:
            handle.read(80)
            count_data = handle.read(4)
            if not count_data:
                return

            count = struct.unpack("<I", count_data)[0]
            file_size = os.path.getsize(self.filepath)
            expected_size = 80 + 4 + (50 * count)
            if file_size != expected_size:
                raise ValueError("Size mismatch")

            for _ in range(count):
                data = handle.read(50)
                floats = struct.unpack("<3f3f3f3f", data[:48])
                attribute = struct.unpack("<H", data[48:50])[0]

                vertex_1 = (floats[3], floats[4], floats[5])
                vertex_2 = (floats[6], floats[7], floats[8])
                vertex_3 = (floats[9], floats[10], floats[11])
                self.triangles.append((vertex_1, vertex_2, vertex_3, attribute))

    def get_volume(self, triangles=None):
        mesh_triangles = triangles if triangles is not None else self.triangles
        total_volume = 0.0
        for triangle in mesh_triangles:
            vertex_1, vertex_2, vertex_3 = triangle[0], triangle[1], triangle[2]
            cp_x = vertex_2[1] * vertex_3[2] - vertex_2[2] * vertex_3[1]
            cp_y = vertex_2[2] * vertex_3[0] - vertex_2[0] * vertex_3[2]
            cp_z = vertex_2[0] * vertex_3[1] - vertex_2[1] * vertex_3[0]
            dot_product = vertex_1[0] * cp_x + vertex_1[1] * cp_y + vertex_1[2] * cp_z
            total_volume += dot_product
        return abs(total_volume) / 6.0

    def get_components(self):
        def quantize(vertex):
            return (round(vertex[0], 5), round(vertex[1], 5), round(vertex[2], 5))

        vertex_map = collections.defaultdict(list)
        for index, triangle in enumerate(self.triangles):
            for vertex in triangle[:3]:
                vertex_map[quantize(vertex)].append(index)

        visited_indices = set()
        components = []

        for start_index in range(len(self.triangles)):
            if start_index in visited_indices:
                continue

            component_indices = []
            queue = collections.deque([start_index])
            visited_indices.add(start_index)

            while queue:
                current_index = queue.popleft()
                component_indices.append(current_index)
                current_triangle = self.triangles[current_index]
                for vertex in current_triangle[:3]:
                    for neighbor_index in vertex_map[quantize(vertex)]:
                        if neighbor_index not in visited_indices:
                            visited_indices.add(neighbor_index)
                            queue.append(neighbor_index)

            components.append([self.triangles[index] for index in component_indices])

        return components

    def analyze_largest_component(self):
        components = self.get_components()
        if not components:
            return {"main_part_volume": 0.0, "main_part_material_id": 0, "total_components": 0}

        component_reports = []
        for component in components:
            volume = self.get_volume(component)
            component_reports.append((volume, component))

        component_reports.sort(key=lambda item: item[0], reverse=True)
        largest_volume, largest_component = component_reports[0]
        material_id = largest_component[0][3]

        return {
            "main_part_volume": largest_volume,
            "main_part_material_id": material_id,
            "total_components": len(components),
        }
