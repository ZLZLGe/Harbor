你会得到一个 JavaScript 3D 场景模块 `/root/data/wind_turbine.js`。该模块导出 `createScene()`，返回一棵包含多个具名 `Group` 的风力发电机场景。

请编写程序解析该场景，并把“具名 `Group`”视为部件。每个 `Mesh` 必须归属到它向上追溯时遇到的最近具名祖先部件；如果一个具名部件下面还有更深层的具名部件，子部件中的 mesh 不应再算到父部件里。

输出要求：

1. 生成部件清单 `/root/output/wind_turbine_manifest.json`。
2. 为每个部件导出该部件名下每个 mesh 的单独 OBJ，保存到 `/root/output/part_meshes/<part_name>/<mesh_name>.obj`。
3. 为每个部件导出一个合并后的 OBJ，保存到 `/root/output/merged_parts/<part_name>.obj`。

清单 JSON 必须满足以下结构：

```json
{
  "scene_file": "/root/data/wind_turbine.js",
  "part_count": 0,
  "parts": [
    {
      "part_name": "example_part",
      "mesh_count": 0,
      "mesh_names": ["mesh_a", "mesh_b"],
      "mesh_obj_paths": [
        "/root/output/part_meshes/example_part/mesh_a.obj",
        "/root/output/part_meshes/example_part/mesh_b.obj"
      ],
      "merged_obj_path": "/root/output/merged_parts/example_part.obj",
      "vertex_count": 0,
      "bbox": {
        "min": [0.0, 0.0, 0.0],
        "max": [0.0, 0.0, 0.0]
      }
    }
  ]
}
```

补充要求：

- `parts` 必须按 `part_name` 升序排序。
- `mesh_names` 和 `mesh_obj_paths` 也必须稳定排序。
- 空部件不要写入清单。
- 导出 OBJ 之前，需要把世界变换烘焙到几何体上。
- 所有路径都必须使用绝对路径。
