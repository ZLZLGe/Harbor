你会得到一个 JavaScript 3D 场景模块 `/root/data/exhibition_hall.js`。该模块导出 `createScene()`，返回一个多区域展馆的层级场景。

请把所有“具名 `Group`”视为分区节点，并生成 `/root/output/zone_bounds_report.json`。

分区与几何归属规则：

- 每个 `Mesh` 只归属到它向上追溯时遇到的最近具名祖先分区。
- 如果某个具名分区内部还有更深层的具名分区，子分区中的 mesh 不能再计入父分区。
- 未归属到任何具名分区的 mesh 不要输出。
- 包围盒必须基于烘焙世界变换后的几何计算；旋转、缩放、嵌套平移都要正确处理。

输出 JSON 必须满足以下结构：

```json
{
  "scene_file": "/root/data/exhibition_hall.js",
  "zone_count": 0,
  "zones": [
    {
      "zone_name": "example_zone",
      "parent_zone": null,
      "child_zones": ["child_zone_a", "child_zone_b"],
      "mesh_count": 0,
      "direct_mesh_names": ["mesh_a", "mesh_b"],
      "world_bbox": {
        "min": [0.0, 0.0, 0.0],
        "max": [0.0, 0.0, 0.0]
      }
    }
  ]
}
```

补充要求：

- `zones` 必须按 `zone_name` 升序排序。
- 每个分区里的 `child_zones` 和 `direct_mesh_names` 也必须按升序排序。
- 只保留至少拥有一个直属 mesh 的分区。
- `parent_zone` 必须是该分区向上追溯时遇到的最近具名祖先分区；根分区填 `null`。
- `world_bbox` 必须是该分区所有直属 mesh 的世界空间包围盒并集。
- 所有路径都必须使用绝对路径。
