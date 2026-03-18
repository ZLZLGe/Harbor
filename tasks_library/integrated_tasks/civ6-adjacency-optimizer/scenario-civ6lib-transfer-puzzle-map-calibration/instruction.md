# Transfer - Puzzle Map Calibration

你现在在做一份 Civilization VI 关卡蓝图校准题。

设计师已经固定了城市中心与所有区域的位置，不允许你改动摆放方案；你只能从给定的少量地图补丁选项里挑选若干项，修改地块属性，让整套蓝图同时满足两件事：

1. 全部区域放置在官规下合法。
2. 校准后的逐区邻接分与目标值完全一致。

## 输入

读取：

- `/data/puzzle_map_calibration/scenario.json`

文件中包含：

- `city_center`
- `population`
- 固定的 `placements`
- 目标 `target_adjacency_bonuses`
- 目标 `target_total_adjacency`
- 基础 `tiles`
- 可选的 `patch_options`

每个 `patch_options` 都只描述一个可启用的地图补丁，包含：

- `patch_id`
- `tile`
- `changes`

你只能对这些候选补丁做二选一取舍，不能自行发明额外修改。

## 你需要做的事

1. 找出能让蓝图合法且达到目标邻接分的最小补丁集合。
2. 如果存在多个同样小的补丁集合，选择 `selected_patch_ids` 按输入顺序比较时最靠前的那一个。
3. 按官方规则重算校准后的逐区邻接分与总邻接分。

## 输出

写入：

- `/output/puzzle_map_calibration.json`

输出必须是合法 JSON，并且精确满足下面结构：

```json
{
  "scenario_id": "puzzle_map_calibration",
  "selected_patch_ids": [
    "clear_campus_luxury",
    "restore_harbor_coast"
  ],
  "patch_count": 2,
  "patched_tiles": [
    {
      "tile": [2, 3],
      "changes": {
        "resource": null,
        "resource_type": null
      }
    }
  ],
  "blueprint_legal": true,
  "calibrated_adjacency_bonuses": {
    "CAMPUS": 3,
    "COMMERCIAL_HUB": 4
  },
  "calibrated_total_adjacency": 7
}
```

## 约束

- `selected_patch_ids` 必须按输入文件里 `patch_options` 的原始顺序输出。
- `patch_count` 必须等于 `selected_patch_ids` 的长度。
- `patched_tiles` 必须与 `selected_patch_ids` 一一对应，顺序一致。
- `blueprint_legal` 必须为 `true`。
- `calibrated_total_adjacency` 必须严格等于 `calibrated_adjacency_bonuses` 的数值总和。
- 不要输出额外字段。
