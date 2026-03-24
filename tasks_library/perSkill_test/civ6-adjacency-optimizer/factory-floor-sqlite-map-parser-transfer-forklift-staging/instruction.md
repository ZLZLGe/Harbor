# 工厂叉车临时集货区规划

你需要根据一个车间布局数据库，给出叉车临时集货区候选位，而不是做完整排程。

## 输入

读取：
- `/data/briefing/transfer_request.json`

其中会给出：
- `layout_db`: 布局数据库路径
- `candidate_lane_codes`: 允许作为候选位的通道类型
- `blocked_overlay_codes`: 视为不可通行的覆盖标记
- `forbidden_overlay_codes`: 虽可通行但禁止临时集货的覆盖标记
- `loading_asset_types`: 装卸口设备类型
- `hazard_asset_types`: 危险设备类型
- `max_dock_steps`: 候选位到最近装卸口的最大通行步数
- `min_hazard_manhattan`: 候选位到任一危险设备的最小曼哈顿距离
- `shortlist_size`: 最多输出多少个候选位

## 目标

从 SQLite 数据库中恢复：
- 车间网格尺寸
- 每个单元格的线性编码与 `(x, y)` 坐标
- 通道 / 缓冲区 / 服务区 / 墙体
- 禁停区、消防通道、阻塞标记
- 装卸口和危险设备位置

然后筛选出可作为叉车临时集货区的候选单元，并把结果写到：
- `/output/forklift_staging_plan.json`

## 有效候选位

某个单元格只有同时满足以下条件，才算有效候选位：

1. 单元格可通行。
2. `lane_code` 属于 `candidate_lane_codes`。
3. 没有 `blocked_overlay_codes` 中的覆盖标记。
4. 没有 `forbidden_overlay_codes` 中的覆盖标记。
5. 该单元格本身没有设备占用。
6. 从任一装卸口出发，只沿可通行且未阻塞的正交相邻单元移动，到该单元格的最短步数不超过 `max_dock_steps`。
7. 该单元格到所有危险设备锚点的曼哈顿距离都至少为 `min_hazard_manhattan`。

## 排序规则

对所有有效候选位排序，规则如下：

1. `dock_steps` 更小者优先
2. `hazard_clearance` 更大者优先
3. `adjacent_open_cells` 更大者优先
4. `cell_ref` 更小者优先

其中 `adjacent_open_cells` 表示该单元格四联通相邻单元中，同时满足“可通行、未阻塞、非禁停、未被设备占用”的数量。

## 输出格式

请严格输出如下结构：

```json
{
  "layout": {
    "floor_name": "Plant 7 Receiving Hall",
    "width": 8,
    "height": 6,
    "cell_size_m": 1.5
  },
  "rules": {
    "candidate_lane_codes": ["AISLE", "BUFFER"],
    "max_dock_steps": 3,
    "min_hazard_manhattan": 3,
    "shortlist_size": 5
  },
  "summary": {
    "traversable_cells": 24,
    "candidate_lane_cells": 20,
    "blocked_cells": 1,
    "forbidden_cells": 2,
    "loading_docks": 2,
    "hazard_sources": 3,
    "valid_candidates": 6
  },
  "loading_docks": [
    {
      "asset_code": "DOCK_A",
      "asset_type": "LOADING_DOCK",
      "display_name": "West inbound dock",
      "cell_ref": 16,
      "x": 0,
      "y": 2
    }
  ],
  "hazards": [
    {
      "asset_code": "HZ_WELD",
      "asset_type": "WELD_STATION",
      "display_name": "Welding booth",
      "cell_ref": 12,
      "x": 4,
      "y": 1
    }
  ],
  "forbidden_cells": [
    {
      "cell_ref": 26,
      "x": 2,
      "y": 3,
      "overlays": ["NO_STAGING"]
    }
  ],
  "candidates": [
    {
      "cell_ref": 17,
      "x": 1,
      "y": 2,
      "lane_code": "AISLE",
      "nearest_dock": "DOCK_A",
      "dock_steps": 1,
      "hazard_clearance": 4,
      "adjacent_open_cells": 3,
      "overlays": []
    }
  ],
  "recommended_cell": {
    "cell_ref": 17,
    "x": 1,
    "y": 2,
    "lane_code": "AISLE",
    "nearest_dock": "DOCK_A",
    "dock_steps": 1,
    "hazard_clearance": 4,
    "adjacent_open_cells": 3,
    "overlays": []
  }
}
```

## 要求

1. JSON 必须合法。
2. `cell_ref` 与 `(x, y)` 的还原必须正确。
3. `summary` 中的计数必须与数据库内容一致。
4. `loading_docks`、`hazards`、`forbidden_cells` 必须按各自主键升序输出。
5. `candidates` 必须已经按题目规则排序，并且长度不超过 `shortlist_size`。
6. `recommended_cell` 必须与排序后的首个候选位完全一致。
