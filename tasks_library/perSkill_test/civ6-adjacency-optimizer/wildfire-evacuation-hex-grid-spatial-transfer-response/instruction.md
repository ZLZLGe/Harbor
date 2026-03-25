# Transfer: 六角网格山火撤离分析

你要为一片山区聚落做山火撤离分析。

## 输入

读取以下两个文件：

- `/data/terrain_map.txt`
- `/data/incidents.json`

### 地图文件

`terrain_map.txt` 是一个等宽字符网格。

- 第一行对应最高的 `y`
- 最后一行对应 `y = 0`
- 每个字符对应一个六角格
- `x` 从左到右递增
- 坐标系使用 **odd-r 偏移六角坐标**

地图字符含义：

- `.`: 可通行、可燃
- `f`: 可通行、可燃
- `r`: 不可通行、不可燃
- `s`: 可通行、不可燃

### 事件文件

`incidents.json` 中给出：

- `villages`: 村庄坐标与 `id`
- `shelters`: 避难所坐标与 `id`
- `ignitions`: 起火点坐标与起火回合 `turn`

## 规则

### 火势传播

1. 火势只能在 **可燃** 地块上传播。
2. 起火点在各自给定的 `turn` 开始燃烧。
3. 从某个已经着火的地块出发，下一回合火势会传播到它的 6 个相邻六角格中的可燃地块。
4. 每个地块的火势到达时间，定义为最早能被任一起火源烧到的回合。
5. 不可燃地块与永远不会被烧到的地块，火势到达时间记为 `null`。

### 撤离

1. 每个村庄的人群都在回合 `0` 从自己的村庄地块出发。
2. 每回合必须移动到一个相邻六角格，不允许原地等待。
3. 只能走 **可通行** 地块。
4. 到达某个地块的回合必须严格早于该地块的火势到达时间。
   - 如果该地块的火势到达时间是 `null`，则可以进入。
5. 路线的起点必须是该村庄坐标，终点必须是某个避难所坐标。

### 最近安全路线的选择

对每个村庄，只保留一条“最近安全路线”：

1. 先选 `travel_turns` 最小的可行路线。
2. 如果最短可行路线通往多个避难所，选 `shelter_id` 字典序更小的。
3. 如果同一避难所下仍有多条并列最短路线，选整条 `path` 的坐标序列按字典序更小的。
   - 比较方式是从前到后比较 `[x, y]` 二元组，先比 `x`，再比 `y`。

如果某个村庄不存在可行路线，则它的撤离结果记为不可行。

## 输出

把结果写入：

- `/output/wildfire_response.json`

输出格式必须是：

```json
{
  "fire_arrival_turns": [
    [1, 1, 2, 3, 4, null, 6, 6],
    [0, null, 3, 4, 5, null, 5, 5]
  ],
  "village_routes": [
    {
      "village_id": "PINEWATCH",
      "feasible": true,
      "chosen_shelter": "SOUTH_HUB",
      "travel_turns": 2,
      "path": [[1, 1], [0, 1], [0, 0]]
    },
    {
      "village_id": "EMBER_HOLLOW",
      "feasible": false,
      "chosen_shelter": null,
      "travel_turns": null,
      "path": []
    }
  ],
  "overall_evacuation_feasible": false
}
```

## 输出要求

1. `fire_arrival_turns` 必须是与输入地图同尺寸的二维数组，行顺序必须与 `terrain_map.txt` 一致，也就是从最高 `y` 到最低 `y`。
2. 数组中的每个值必须是整数或 `null`。
3. `village_routes` 必须按 `incidents.json` 中 `villages` 的原始顺序输出。
4. 每个村庄都必须恰好输出一项，字段固定为：
   - `village_id`
   - `feasible`
   - `chosen_shelter`
   - `travel_turns`
   - `path`
5. 若 `feasible = true`：
   - `chosen_shelter` 必须是某个避难所 `id`
   - `travel_turns` 必须是整数
   - `path` 必须是从村庄到避难所的完整坐标序列，长度必须等于 `travel_turns + 1`
6. 若 `feasible = false`：
   - `chosen_shelter` 必须是 `null`
   - `travel_turns` 必须是 `null`
   - `path` 必须是空数组
7. `overall_evacuation_feasible` 仅当所有村庄都可撤离时才为 `true`，否则为 `false`。
