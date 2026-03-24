# Civ6 单城定居点情报

你需要为一个单城开局生成定居点情报，而不是直接做完整布局求解。

## 输入

读取：
- `/data/briefing/settlement_brief.json`

其中会给出：
- `map_file`: WorldBuilder 导出的 `.Civ6Map` 文件路径
- `search_radius`: 统计范围，固定为 3
- `shortlist_size`: 每类候选位输出数量
- `planning_score_weights`: 城市中心评分权重

## 目标

从 `.Civ6Map` 中恢复地图尺寸、地块坐标、地形、地貌与河流信息，然后在所有可定居陆地格中选出一个最佳城市中心候选，并输出它 3 格范围内与区域规划直接相关的结构化摘要。

把结果写到：
- `/output/settlement_dossier.json`

## 可定居城市中心

候选城市中心必须满足：
- 不是 `TERRAIN_OCEAN`
- 不是 `TERRAIN_COAST`
- 不是不可通行地块

## 评分与排序

对每个候选城市中心，统计 3 格范围内（不含城市中心自身）的以下信号：

- `campus_signal`: 山脉地块数量 + 地热裂缝地块数量
- `commercial_signal`: 有至少一条河边的可通行陆地格数量
- `coastal_access_signal`: 海岸格数量
- `feature_signal`: `FEATURE_FOREST`、`FEATURE_JUNGLE`、`FEATURE_FLOODPLAINS_PLAINS` 的数量

城市中心总分：

```text
planning_score =
  3 * campus_signal +
  2 * commercial_signal +
  1 * coastal_access_signal +
  1 * feature_signal
```

如果总分并列，依次使用以下规则打破平局：
1. `campus_signal` 更高者优先
2. `commercial_signal` 更高者优先
3. `plot_id` 更小者优先

## 候选区域位摘要

基于选出的最佳城市中心，继续统计 3 格范围内的区域规划摘要：

### `district_shortlist.campus`

从 3 格范围内所有可通行陆地格中选出前 `shortlist_size` 个校园候选位，按以下分数排序：

```text
campus_site_score =
  2 * adjacent_mountains +
  2 * adjacent_geothermal +
  1 * adjacent_reefs
```

平局时按 `plot_id` 升序。

### `district_shortlist.commercial_hub`

从 3 格范围内所有可通行陆地格中选出前 `shortlist_size` 个商业中心候选位，按以下分数排序：

```text
commercial_hub_site_score =
  (2 if river_touched else 0) +
  adjacent_coast_tiles
```

平局时按 `plot_id` 升序。

### `harbor_access`

这里不要求给出港口候选位排序，但要输出：
- `coast_tiles_in_range`: 3 格范围内海岸格数量
- `nearest_coast_tiles`: 最近的前 `shortlist_size` 个海岸格，按 `(distance, plot_id)` 排序

## 输出格式

请严格输出如下结构：

```json
{
  "map": {
    "width": 44,
    "height": 26,
    "wrap_x": true,
    "map_name": "example"
  },
  "best_city_center": {
    "plot_id": 0,
    "x": 0,
    "y": 0,
    "planning_score": 0,
    "score_breakdown": {
      "campus_signal": 0,
      "commercial_signal": 0,
      "coastal_access_signal": 0,
      "feature_signal": 0
    }
  },
  "radius_3_summary": {
    "total_tiles": 0,
    "land_tiles": 0,
    "coast_tiles": 0,
    "ocean_tiles": 0,
    "mountain_tiles": 0,
    "river_land_tiles": 0,
    "geothermal_tiles": 0,
    "forest_or_jungle_tiles": 0,
    "floodplains_tiles": 0
  },
  "district_shortlist": {
    "campus": [
      {
        "plot_id": 0,
        "x": 0,
        "y": 0,
        "score": 0,
        "adjacent_mountains": 0,
        "adjacent_geothermal": 0,
        "adjacent_reefs": 0
      }
    ],
    "commercial_hub": [
      {
        "plot_id": 0,
        "x": 0,
        "y": 0,
        "score": 0,
        "river_touched": false,
        "adjacent_coast_tiles": 0
      }
    ]
  },
  "harbor_access": {
    "coast_tiles_in_range": 0,
    "nearest_coast_tiles": [
      {
        "plot_id": 0,
        "x": 0,
        "y": 0,
        "distance": 0
      }
    ]
  }
}
```

## 要求

1. JSON 必须合法。
2. 坐标、`plot_id`、距离和各类统计都必须与地图内容一致。
3. 所有 shortlist 必须已经按题目要求排好序。
