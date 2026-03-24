你会得到一个 JavaScript 3D 场景模块 `/root/data/stadium_lighting.js`。该模块导出 `createScene()`，返回一个体育馆灯阵场景。

请只统计场景中属于灯具的 `InstancedMesh`。每个具名 `Group` 都代表一个灯架，灯具实例应归属到它向上追溯时遇到的最近具名灯架；未归属到任何具名灯架的实例不要输出。普通 `Mesh` 只是支撑结构，不属于灯具清点范围。

你需要输出两类结果：

1. 生成灯架清单 `/root/output/lighting_inventory.json`。
2. 为每个非空灯架导出一个合并后的 OBJ，保存到 `/root/output/rig_meshes/<rig_name>.obj`。

`/root/output/lighting_inventory.json` 必须满足以下结构：

```json
{
  "scene_file": "/root/data/stadium_lighting.js",
  "rig_count": 0,
  "total_fixture_count": 0,
  "rigs": [
    {
      "rig_name": "example_rig",
      "fixture_count": 0,
      "fixture_types": [
        {
          "type_name": "example_bank",
          "count": 0
        }
      ],
      "merged_obj_path": "/root/output/rig_meshes/example_rig.obj",
      "bbox": {
        "min": [0.0, 0.0, 0.0],
        "max": [0.0, 0.0, 0.0]
      },
      "fixtures": [
        {
          "fixture_name": "example_bank_00",
          "source_type": "example_bank",
          "center": [0.0, 0.0, 0.0],
          "bbox": {
            "min": [0.0, 0.0, 0.0],
            "max": [0.0, 0.0, 0.0]
          }
        }
      ]
    }
  ]
}
```

补充要求：

- `rigs` 必须按 `rig_name` 升序排序。
- 每个灯架里的 `fixture_types` 必须按 `type_name` 升序排序。
- 每个灯架里的 `fixtures` 必须按 `fixture_name` 升序排序。
- `fixture_name` 格式固定为 `<instanced_mesh_name>_<两位序号>`，例如 `beam_spots_00`。
- `center` 必须是该实例局部原点变换到世界坐标后的结果。
- `bbox` 必须基于展开到世界坐标后的单个实例几何计算；灯架级 `bbox` 是该灯架所有灯具实例包围盒的并集。
- 导出 OBJ 前，必须把每个实例的局部矩阵与场景层级矩阵合成为世界变换，并烘焙到几何体上。
- 所有路径都必须使用绝对路径。
