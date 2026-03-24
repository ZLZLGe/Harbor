# Similar: Civ6 District Surface Exporter

读取下面这个侦察请求，并生成一个结构化 JSON，供后续规划器消费：

- `/data/request/surface_request.json`

请求文件会包含若干字段，其中：
- `map_file` 是一个 Civilization VI 的 `.Civ6Map` SQLite 地图文件
- `candidate_city_center` 是候选城市中心坐标 `[x, y]`
- `ring_radius` 是需要导出的城市圈层半径

请求里也可能带有 `district_types`、`population`、`description` 之类的下游元数据。本任务不需要按区域类型做精确落位判定，但必须把整个请求文件原样回显到输出里的 `request` 字段。

你的任务是：
1. 解析 `.Civ6Map` 中与地块相关的 SQLite 表，导出整张地图的地表数据。
2. 围绕 `candidate_city_center` 计算 `1..ring_radius` 内的所有地块，并给出一个“通用陆地区块候选”标记。
3. 这个候选标记只允许依赖本说明中显式定义的阻塞条件，不能引入其他游戏规则或额外假设。

把结果写到：
- `/output/civ6_district_surface.json`

输出 JSON 必须满足以下结构：

```json
{
  "map": {
    "width": 44,
    "height": 26,
    "plot_count": 1144
  },
  "request": {
    "id": "surface_export_request",
    "description": "Export the full map surface and district buildability around a fixed city center.",
    "map_file": "/data/maps/e2e_test_case_0.Civ6Map",
    "candidate_city_center": [21, 13],
    "ring_radius": 3,
    "population": 9,
    "district_types": ["CAMPUS", "HOLY_SITE"]
  },
  "plots": [
    {
      "plot_id": 0,
      "x": 0,
      "y": 0,
      "terrain_type": "TERRAIN_OCEAN",
      "is_hills": false,
      "feature_type": "FEATURE_ICE",
      "is_water": true,
      "is_mountain": false,
      "river_edges": [],
      "resource_type": null,
      "resource_count": null
    }
  ],
  "city_center_surface": {
    "city_center": [21, 13],
    "ring_radius": 3,
    "ring_plots": [
      {
        "plot_id": 460,
        "x": 20,
        "y": 10,
        "distance": 3,
        "blockers": ["water"],
        "is_general_land_district_candidate": false
      }
    ],
    "summary": {
      "ring_plot_count": 36,
      "candidate_plot_count": 12,
      "blocked_plot_count": 24
    }
  }
}
```

字段定义与判定规则：

1. `request` 必须是输入请求文件的逐字段原样回显，不允许删字段、改值或重排列表内容。
2. `map.width` 与 `map.height` 来自 SQLite 中 `Map` 表的 `Width`、`Height`。
3. `plot_id` 来自 `Plots.ID`。
4. 每个地块的坐标必须按下面公式计算：
   - `x = plot_id % width`
   - `y = plot_id // width`
5. `plots` 中每个元素都必须包含以下字段：
   - `terrain_type`: `Plots.TerrainType` 原值
   - `is_hills`: 当 `terrain_type` 以 `_HILLS` 结尾时为 `true`，否则为 `false`
   - `feature_type`: `PlotFeatures.FeatureType`；如果 `PlotFeatures` 表不存在或该地块没有记录，则为 `null`
   - `is_water`: 当 `terrain_type` 属于 `TERRAIN_COAST`、`TERRAIN_OCEAN`、`TERRAIN_LAKE` 时为 `true`，否则为 `false`
   - `is_mountain`: 当 `terrain_type` 以 `_MOUNTAIN` 结尾时为 `true`，否则为 `false`
   - `river_edges`: 从 `PlotRivers` 生成的升序整数数组；映射规则固定为：
     - `EFlowDirection != -1` 时加入 `0`
     - `IsNEOfRiver == 1` 时加入 `1`
     - `IsNWOfRiver == 1` 时加入 `2`
     - `IsWOfRiver == 1` 时加入 `3`
     - `SWFlowDirection != -1` 时加入 `4`
     - `SEFlowDirection != -1` 时加入 `5`
     - 如果 `PlotRivers` 表不存在或该地块没有记录，则输出空数组
   - `resource_type`: `PlotResources.ResourceType`；如果 `PlotResources` 表不存在或该地块没有记录，则为 `null`
   - `resource_count`: `PlotResources.ResourceCount`；如果 `PlotResources` 表不存在或该地块没有记录，则为 `null`
6. `city_center_surface.ring_plots` 只包含与 `candidate_city_center` 的六边形距离在 `1..ring_radius` 的地块。
7. 六边形距离必须按下面的 odd-r offset 转 cube 公式计算：
   - 对任意 `(x, y)`，令 `cx = x - (y - (y & 1)) // 2`
   - `cz = y`
   - `cy = -cx - cz`
   - 两点距离为 `(abs(cx1 - cx2) + abs(cy1 - cy2) + abs(cz1 - cz2)) // 2`
8. 每个 `ring_plots` 元素的 `blockers` 只能来自下面这 4 个代码，并且必须严格按这个顺序输出其适用子集：
   - `water`: 当 `is_water == true`
   - `mountain`: 当 `is_mountain == true`
   - `geothermal_fissure`: 当 `feature_type == "FEATURE_GEOTHERMAL_FISSURE"`
   - `resource_present`: 当 `resource_type != null`
9. `is_general_land_district_candidate` 必须等于 `len(blockers) == 0`。
10. `city_center_surface.summary` 中：
    - `ring_plot_count` 等于 `ring_plots` 的元素个数
    - `candidate_plot_count` 等于 `is_general_land_district_candidate == true` 的地块数
    - `blocked_plot_count` 等于 `is_general_land_district_candidate == false` 的地块数

排序要求：
- `plots` 必须按 `plot_id` 升序输出。
- `city_center_surface.ring_plots` 必须按 `plot_id` 升序输出。

输出必须是合法 JSON，不要附带解释文字。
