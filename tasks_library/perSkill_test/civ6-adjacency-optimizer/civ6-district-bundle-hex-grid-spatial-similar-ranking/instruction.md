# Similar: 文明6候选区域组合规划

你要为一个固定单城做三区域组合规划。

## 输入

读取场景文件：

- `/data/bundle_scenario.json`

场景中已经给出：

- 固定城市中心 `city_center`
- 城市可用半径 `city_radius`
- 必须选择的区域数量 `required_bundle_size`
- 候选区域列表 `candidate_districts`
- 每种区域的放置约束与邻接计分规则 `district_rules`
- 局部六角地图 `tiles`

坐标系使用 **odd-r 偏移六角坐标**：

- `x` 向右增加，`y` 向上增加
- 奇数行右移半格
- 六个相邻格必须按这种坐标系计算

## 任务

从 `candidate_districts` 中选出恰好 3 个不同区域，并为每个区域选择一个合法地块，使 `total_adjacency` 最大。

你必须同时满足：

1. 每个区域只能放在 `tiles` 中 `buildable = true` 的地块上。
2. 不能放在城市中心。
3. 必须位于城市中心三环内，也就是与 `city_center` 的六角距离不超过 `city_radius`。
4. 三个区域不能重叠。
5. 必须满足各区域在 `district_rules` 中定义的自地块标签要求与禁放标签。

## 邻接分规则

对每个已选区域：

1. 只看它周围 6 个相邻六角格。
2. 如果某个相邻格被另一个已选区域占用，则只获得该区域的 `adjacent_district_bonus`。
3. 如果某个相邻格没有被已选区域占用，则按该格 `tags` 中命中的 `adjacency_from_neighbor_tags` 计分。
4. `occupied_tiles_block_neighbor_tags = true`，因此被区域占用的格子不再提供自然标签邻接分。

最终：

- `total_adjacency` 必须等于三个区域 `adjacency` 之和。
- 你提交的组合必须是全局最优解；如果有并列最优，任意一个并列最优布局都算正确。

## 输出

把结果写入：

- `/output/civ6_bundle_plan.json`

输出格式必须是：

```json
{
  "city_center": [4, 4],
  "chosen_districts": [
    {
      "district": "CAMPUS",
      "location": [4, 3],
      "adjacency": 6
    },
    {
      "district": "COMMERCIAL_HUB",
      "location": [5, 4],
      "adjacency": 6
    },
    {
      "district": "THEATER_SQUARE",
      "location": [4, 5],
      "adjacency": 5
    }
  ],
  "total_adjacency": 17
}
```

额外要求：

- `chosen_districts` 必须恰好有 3 项
- `district` 必须来自 `candidate_districts`
- 三个 `district` 必须互不重复
- 每个 `location` 必须是 `[x, y]`
- `adjacency` 和 `total_adjacency` 必须是整数
- `city_center` 必须与输入一致

