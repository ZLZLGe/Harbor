# Transfer - 双城联动邻接优化

## 任务

在同一张 Civilization VI 地图上建立一个双城帝国。

场景文件位于：
- `/data/two_city_empire/scenario.json`

你需要：
- 为 `city_alpha` 从它的候选坐标中选择 1 个城市中心
- 为 `city_beta` 从它的候选坐标中选择 1 个城市中心
- 将场景里的固定 `district_pool` 中每个区划恰好建造 1 次，并明确分配给其中一座城市
- 为每个区划选择落位，使全局总邻接最大化

标准 Civilization VI 规则仍然生效，包括：
- 城市中心之间的最小距离
- 区划必须在所属城市中心 3 格范围内
- 地形与区划落位合法性
- 人口决定的特色区划上限
- 区划与城市中心不可重叠
- 文明级唯一规则

## 输入

`/data/two_city_empire/scenario.json` 提供：
- `map_file`: 原始 `.Civ6Map`
- `city_slots`: 两个城市槽位，各自的人口与可选城市中心
- `district_pool`: 需要被完整放置的一组区划
- `civilization`: 当前文明

## 输出

把结果写入：
- `/output/two_city_empire_plan.json`

输出格式必须是：

```json
{
  "cities": {
    "city_alpha": {
      "center": [21, 13],
      "placements": {
        "CAMPUS": [21, 14],
        "INDUSTRIAL_ZONE": [22, 14],
        "AQUEDUCT": [22, 13],
        "DAM": [23, 14]
      },
      "adjacency_bonuses": {
        "CAMPUS": 7,
        "INDUSTRIAL_ZONE": 5,
        "AQUEDUCT": 0,
        "DAM": 0
      },
      "total_adjacency": 12
    },
    "city_beta": {
      "center": [22, 17],
      "placements": {
        "HARBOR": [23, 18],
        "COMMERCIAL_HUB": [23, 17],
        "GOVERNMENT_PLAZA": [23, 16]
      },
      "adjacency_bonuses": {
        "HARBOR": 2,
        "COMMERCIAL_HUB": 5,
        "GOVERNMENT_PLAZA": 0
      },
      "total_adjacency": 7
    }
  },
  "total_adjacency": 19
}
```

## 要求

1. `cities` 必须且只能包含 `city_alpha` 与 `city_beta`。
2. 每个城市中心都必须来自对应槽位的候选坐标。
3. `district_pool` 中的每个区划必须恰好出现一次，不能缺失，也不能重复。
4. 每座城市的 `total_adjacency` 必须等于该城市 `adjacency_bonuses` 的和。
5. 顶层 `total_adjacency` 必须等于两座城市总和。
6. 所有落位必须合法，且所有邻接计算必须正确。

## 评分

- 任一格式或合法性错误：得分为 `0`
- 否则：`your_total_adjacency / optimal_total_adjacency`，上限为 `1.0`

存在多种最优输出时，任意一个最优合法方案都可得满分。
