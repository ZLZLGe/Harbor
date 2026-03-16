# Cold Chain Warehouse Transfer - Pickface Slotting

你要在一张冷链仓库方格图上，为拣货位和补给设施做一次合法且高分的布局。

## 场景文件

读取：

- `/data/warehouse_scenario.json`

## 你要决定的设施

必须恰好放置：

- 2 个 `PICKFACE`
- 1 个 `BUFFER`
- 1 个 `REPLENISHMENT`
- 1 个 `CHARGER`

所有设施都必须放在场景中列出的 `slots` 坐标上，并且每个坐标只能放一个设施。

## 巷道与可达性

- 仓库使用二维方格坐标，四联通移动。
- 只有场景中的 `aisles` 坐标可以作为巷道通行。
- `dock` 是唯一的入库/出库起点。
- 一个 `slot` 只有在它至少有一个相邻巷道格，且该巷道能从 `dock` 走到时，才允许放设施。
- 设施之间的支持收益与部分拥堵惩罚都按巷道最短路距离计算：
  - 先从起点设施进入任一相邻可达巷道
  - 沿巷道最短路移动
  - 再从巷道离开到目标设施

## 容量与间距硬约束

1. 每种设施数量必须完全符合 `required_counts`。
2. 每个设施会消耗 `capacity_loads` 中对应的容量。
3. 每个分区的总容量不能超过 `zone_capacity_limits`。
4. 任意两个 `PICKFACE` 的曼哈顿距离必须 `>= 4`。
5. 任意 `CHARGER` 与任意 `PICKFACE` 的曼哈顿距离必须 `>= 3`。
6. 禁放位和不可达位都不能使用。

## 计分方式

每个被选中的 `slot` 对不同设施角色都有三项本地指标：

- `throughput`
- `handling_cost`
- `congestion`

先把 5 个已放设施对应角色的三项本地指标分别求和，然后再叠加规则分：

- `support_bonus_rules` 会增加 `throughput_reward`
- `extra_congestion_rules` 会增加 `congestion_penalty`

最终：

`total_score = throughput_reward - handling_cost - congestion_penalty`

其中：

- `support_bonus_rules[*].max_travel_distance` 使用巷道最短路距离判断
- `extra_congestion_rules` 里的 `same_zone` 规则只要对应两类设施落在同一 `zone` 就会触发

## 输出

把答案写到：

- `/output/warehouse_slotting_plan.json`

输出必须是合法 JSON，格式如下：

```json
{
  "pickfaces": [[1, 1], [5, 3]],
  "buffer": [3, 1],
  "replenishment": [3, 5],
  "charger": [1, 5],
  "capacity_used": 15,
  "score_breakdown": {
    "throughput_reward": 122,
    "handling_cost": 27,
    "congestion_penalty": 16,
    "total_score": 79
  }
}
```

额外要求：

- `pickfaces` 必须包含恰好 2 个不同坐标
- `capacity_used` 必须等于实际放置设施容量之和
- `score_breakdown.total_score` 必须等于前三项按公式计算得到的值
- 坐标顺序不限，但输出中的分数必须与你的布局严格一致
