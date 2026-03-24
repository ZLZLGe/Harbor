# Wetland Reserve Transfer - Habitat Corridor Planner

你要在一张湿地保护区地图上，为目标物种设计一套兼顾连通性与监测覆盖的布局方案。

## 场景文件

读取：

- `/data/wetland_reserve_scenario.json`

## 你要放置的设施

必须恰好放置：

- 2 个 `NEST_BOX`
- 2 个 `BUFFER`
- 1 个 `MONITOR`

所有设施都必须放在场景 `sites` 中列出的坐标上，并且每个坐标最多放一个设施。

## 可达性与距离

- 地图使用二维方格坐标，四联通移动。
- `corridor_cells` 表示保护区中可用于巡护和连通计算的可达廊道。
- `entry` 是巡护网络入口，只有从该入口可达的廊道才算有效。
- 一个 `site` 只有在它至少有一个相邻廊道格，并且该廊道可从 `entry` 到达时，才允许放设施。
- 设施之间的距离，以及设施到 `habitat_patches` 的距离，都按廊道最短路计算：
  - 从设施所在格进入任一相邻可达廊道
  - 沿廊道最短路移动
  - 到达目标设施相邻廊道，或直接到达目标 habitat patch

## 风险与硬约束

1. `blocked = true` 的站位不能使用，这些点代表洪涝高风险区或施工冲突区。
2. 每种设施数量必须完全符合 `required_counts`。
3. `zone_capacity_costs` 与 `zone_capacity_limits` 一起定义各分区可承载的总布设负荷，任何分区都不能超限。
4. 任意两个 `NEST_BOX` 的曼哈顿距离必须 `>= 4`。
5. `MONITOR` 与任意 `NEST_BOX` 的曼哈顿距离必须 `>= 3`，以避免监测干扰繁殖点。
6. 输出中的容量统计与分数必须和你的实际布局严格一致。

## 计分方式

每个被选中的站位，对不同设施角色都有两项本地指标：

- `habitat_value`
- `installation_cost`

同时每个站位还有一个 `noise_level`。不同设施承受噪声的权重由 `noise_penalty_weights` 给出。

最终分数由以下部分组成：

1. `base_habitat`
   - 把 5 个已放设施对应角色的 `habitat_value` 求和。
2. `coverage_bonus`
   - 对每个 `habitat_patch`，分别判断是否被至少一个 `NEST_BOX`、至少一个 `BUFFER`、以及 `MONITOR` 覆盖。
   - 覆盖阈值由 `coverage_radius` 给出，奖励值写在 patch 的 `nest_bonus`、`buffer_bonus`、`monitor_bonus` 中。
   - 同一个 patch 的三类奖励彼此独立，满足就各加一次。
3. `support_bonus`
   - 依据 `support_bonus_rules`，只要满足对应角色组合的最大廊道距离，就获得奖励。
4. `network_bonus`
   - 如果 5 个设施在 `network_bonus.max_link_distance` 规则下构成一个连通网络，就获得额外奖励。
5. `installation_cost`
   - 为所有设施对应角色的 `installation_cost` 之和。
6. `noise_penalty`
   - 对每个设施，按 `noise_level * noise_penalty_weights[role]` 累加。

最终：

`total_score = base_habitat + coverage_bonus + support_bonus + network_bonus - installation_cost - noise_penalty`

## 输出

把答案写到：

- `/output/wetland_corridor_plan.json`

输出必须是合法 JSON，格式如下：

```json
{
  "nest_boxes": [[1, 1], [3, 5]],
  "buffers": [[1, 3], [5, 5]],
  "monitoring_point": [5, 3],
  "zone_capacity_used": {
    "north": 3,
    "central": 4,
    "south": 5,
    "east": 0
  },
  "score_breakdown": {
    "base_habitat": 70,
    "coverage_bonus": 84,
    "support_bonus": 14,
    "network_bonus": 10,
    "installation_cost": 18,
    "noise_penalty": 13,
    "total_score": 147
  }
}
```

额外要求：

- `nest_boxes` 必须包含恰好 2 个不同坐标
- `buffers` 必须包含恰好 2 个不同坐标
- 所有坐标都必须来自场景中的合法站位
- `zone_capacity_used` 必须等于实际放置设施的分区负荷
- `score_breakdown.total_score` 必须等于其余字段按公式计算得到的结果
