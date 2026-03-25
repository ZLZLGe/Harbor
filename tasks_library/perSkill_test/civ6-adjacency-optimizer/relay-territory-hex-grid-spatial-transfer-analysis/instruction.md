# Transfer: 六角通信服务区归属分析

你要为一片蜂巢式通信覆盖区做服务归属分析。

## 输入

读取以下两个文件：

- `/data/relay_cells.csv`
- `/data/network_assets.json`

### `relay_cells.csv`

这是通信研究区内的全部已登记六角格列表，字段固定为：

- `x`
- `y`
- `cell_type`

其中：

- `cell_type = service` 表示可纳入服务区统计的有效通信格
- `cell_type = shadow` 表示屏蔽格，只作为地图背景存在，不属于任何基站服务区，也不计入争议格

没有出现在 `relay_cells.csv` 中的坐标，视为研究区外部，完全忽略。

### `network_assets.json`

文件中给出：

- `coordinate_system`: 坐标系说明，本题固定为 `odd-r`
- `base_stations`: 基站列表，每项包含 `id`、`x`、`y`
- `inspection_points`: 巡检点列表，每项包含 `id`、`x`、`y`

坐标规则：

- 使用 **odd-r 偏移六角坐标**
- `x` 向右增加，`y` 向上增加
- 奇数行右移半格

## 任务

基于六角距离完成三件事：

1. 对每个巡检点，找出最近的基站并输出归属结果。
2. 对每个 `service` 格，按最近基站划分服务区。
3. 找出所有与两个或以上基站等距的 `service` 格，并把这些格标记为争议格。

## 规则

### 距离与归属

1. 所有距离都按 **odd-r 六角距离** 计算。
2. 屏蔽格 `shadow` 不会改变距离计算方式；它们只是不能被纳入服务区，也不能被列为争议格。
3. 对一个 `service` 格：
   - 如果存在唯一最近基站，该格归属于该基站。
   - 如果有两个或以上基站并列最近，该格是争议格，不归属于任何基站。
4. `service_area_size` 只统计唯一归属给该基站的 `service` 格数量。
5. 基站自身所在格如果是 `service` 格，也要计入对应服务区。

### 巡检点

1. 对每个巡检点，输出最近基站的 `id` 和六角距离。
2. 本题给定数据中，每个巡检点都存在唯一最近基站。

## 输出

把结果写入：

- `/output/relay_territories.json`

输出格式必须是：

```json
{
  "station_territories": [
    {
      "station_id": "NORTH_RELAY",
      "service_area_size": 6,
      "cells": [[0, 2], [0, 3], [1, 3], [1, 4], [2, 4], [3, 4]]
    }
  ],
  "disputed_cells": [
    {
      "x": 1,
      "y": 2,
      "nearest_station_ids": ["NORTH_RELAY", "SOUTH_RELAY"],
      "distance": 2
    }
  ],
  "inspection_assignments": [
    {
      "checkpoint_id": "CP_ALPHA",
      "assigned_station_id": "SOUTH_RELAY",
      "distance": 2
    }
  ]
}
```

## 输出要求

1. 顶层字段固定为：
   - `station_territories`
   - `disputed_cells`
   - `inspection_assignments`
2. `station_territories`：
   - 必须按 `network_assets.json` 中 `base_stations` 的原始顺序输出
   - 每项字段固定为 `station_id`、`service_area_size`、`cells`
   - `cells` 必须列出该基站全部唯一归属的 `service` 格坐标，按 `[x, y]` 的字典序升序排列
   - `service_area_size` 必须等于 `cells` 的数量
3. `disputed_cells`：
   - 只包含 `service` 格
   - 必须按 `(x, y)` 字典序升序排列
   - 每项字段固定为 `x`、`y`、`nearest_station_ids`、`distance`
   - `nearest_station_ids` 必须列出全部并列最近基站的 `id`，按字典序升序排列
4. `inspection_assignments`：
   - 必须按 `network_assets.json` 中 `inspection_points` 的原始顺序输出
   - 每项字段固定为 `checkpoint_id`、`assigned_station_id`、`distance`
   - `assigned_station_id` 必须是该巡检点唯一最近基站的 `id`
   - `distance` 必须是该巡检点到该基站的六角距离
5. 任何 `shadow` 格都不能出现在 `station_territories.cells` 或 `disputed_cells` 中。
6. 输出必须是合法 JSON。
