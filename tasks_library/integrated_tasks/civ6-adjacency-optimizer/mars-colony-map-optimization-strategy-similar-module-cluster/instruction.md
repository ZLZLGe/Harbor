# Mars Colony Similar - Module Cluster Optimizer

你要为一张六边形火星殖民地图规划一个高收益模块簇。

## 任务目标

读取场景文件：

- `/data/mars_scenario.json`

你需要决定：

- 指挥穹顶 `command_dome` 放在哪个坐标
- 1 个 `RESEARCH` 模块放在哪个坐标
- 1 个 `INDUSTRIAL` 模块放在哪个坐标
- 2 个 `LIFE_SUPPORT` 模块分别放在哪两个坐标

目标是在满足全部硬约束的前提下，让总协同收益 `total_synergy` 最大。

## 地图与距离

- 地图使用 odd-r 横向偏移六边形坐标
- 供给半径与相邻关系都按六边形距离计算
- 只有场景 JSON 中列出的 tile 才存在
- `buildable = false` 的 tile 不能放任何建筑，但它们仍然会提供邻接标记收益

## 硬约束

1. 必须恰好放置 1 个指挥穹顶、1 个科研模块、1 个工业模块、2 个生命维持模块。
2. 指挥穹顶只能放在 `flat` 或 `plateau`。
3. `RESEARCH` 只能放在 `flat` 或 `plateau`。
4. `INDUSTRIAL` 只能放在 `flat` 或 `dust`。
5. `LIFE_SUPPORT` 只能放在 `ice`。
6. 所有模块都必须位于指挥穹顶六边形距离 `<= supply_radius` 的范围内。
7. 不允许重叠放置。
8. `INDUSTRIAL` 不能与任意 `LIFE_SUPPORT` 相邻。
9. 人口槽位上限为 `population_slots`，槽位消耗为：
   - `RESEARCH = 2`
   - `INDUSTRIAL = 2`
   - `LIFE_SUPPORT = 1`

## 协同收益

每个模块的 `synergy` 单独计算，总和必须等于 `total_synergy`：

- `RESEARCH`
  - 每个相邻 `science_site` +2
  - 若相邻指挥穹顶 +1
  - 每个相邻 `LIFE_SUPPORT` +1
- `INDUSTRIAL`
  - 每个相邻 `ore_field` +2
  - 每个相邻 `power_node` +1
  - 若相邻指挥穹顶 +1
- `LIFE_SUPPORT`
  - 每个相邻 `ice_vent` +2
  - 若相邻指挥穹顶 +1
  - 每个相邻 `RESEARCH` +1

## 输出格式

将答案写到：

- `/output/mars_colony_plan.json`

输出必须是合法 JSON，格式如下：

```json
{
  "command_dome": [3, 3],
  "modules": [
    {"type": "RESEARCH", "coord": [4, 3], "synergy": 5},
    {"type": "INDUSTRIAL", "coord": [3, 2], "synergy": 4},
    {"type": "LIFE_SUPPORT", "coord": [3, 5], "synergy": 4},
    {"type": "LIFE_SUPPORT", "coord": [2, 4], "synergy": 2}
  ],
  "population_used": 6,
  "total_synergy": 15
}
```

额外要求：

- `modules` 中 4 个对象的顺序不限
- `population_used` 必须等于你实际放置模块的槽位消耗总和
- `total_synergy` 必须等于全部 `modules[*].synergy` 之和
