# Festival Grounds Transfer - Amenity Layout

你要为一张音乐节场地图做设施布局优化。

## 场景文件

读取：

- `/data/festival_scenario.json`

## 你必须放置的设施

必须恰好放置：

- 1 个 `main_stage`
- 2 个 `food_courts`
- 2 个 `water_points`
- 1 个 `first_aid_station`

所有设施都只能放在场景文件给出的 `candidate_sites` 坐标上，且每个坐标最多放 1 个设施。

## 硬约束

1. `prohibited_sites` 不能使用。
2. `evacuation_corridors` 是必须留空的疏散通道，任何设施都不能占用这些坐标。
3. 主舞台必须满足 `stage_noise_buffer`：它到每个 `quiet_zone_tiles` 坐标的曼哈顿距离都必须大于等于 `min_distance`。
4. `safety_distance_rules` 中的最小距离约束都必须满足。
5. 不允许输出额外设施，也不允许遗漏设施。

## 计分方式

每个已选 `candidate_site` 都带有按设施角色区分的 `role_site_values`。

再结合热点人流与设施协同，计算：

- `site_value`：6 个设施各自站点分之和
- `crowd_coverage_reward`：若某设施到某热点的曼哈顿距离不超过 `coverage_radius_by_role` 对应半径，就加上 `round(crowd_weight * role_weights[role])`
- `support_bonus`：按 `support_bonus_rules` 逐条判断，只要一对设施满足最大距离，就加对应 bonus
- `distance_penalty`：按 `distance_penalty_rules` 计算；若某条规则涉及的两类设施之间最近曼哈顿距离超过 `max_distance`，则罚分为超出的格数乘 `penalty_per_tile`

最终：

`total_score = site_value + crowd_coverage_reward + support_bonus - distance_penalty`

如果有多个合法布局达到同样高的 `total_score`，选择下面这个坐标序列按字典序最小的方案：

1. `main_stage`
2. `food_courts` 按坐标升序排序后的两个坐标
3. `water_points` 按坐标升序排序后的两个坐标
4. `first_aid_station`

## 输出

把答案写到：

- `/output/festival_layout_plan.json`

输出必须是合法 JSON，并严格满足下面结构：

```json
{
  "main_stage": [3, 3],
  "food_courts": [[1, 5], [5, 3]],
  "water_points": [[1, 3], [3, 5]],
  "first_aid_station": [5, 5],
  "score_breakdown": {
    "site_value": 78,
    "crowd_coverage_reward": 113,
    "support_bonus": 38,
    "distance_penalty": 0,
    "total_score": 229
  }
}
```

额外要求：

- `food_courts` 与 `water_points` 都必须按坐标升序输出。
- `score_breakdown.total_score` 必须严格等于前面三项相加再减去 `distance_penalty` 的结果。
- 输出中的分数必须与你的实际布局严格一致。
- 不要输出额外字段。
