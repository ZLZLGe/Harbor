# Transfer - 海岸基建走廊规划

## 任务

场景文件位于：
- `/data/coastal_corridor/scenario.json`

你需要在同一张 `.Civ6Map` 上完成一个单城海岸经济规划：
- 从 `candidate_city_centers` 中选择 1 个城市中心
- 将 `district_pool` 里的每个区划都恰好建造 1 次
- 在遵守 Civilization VI 区划规则的前提下，最大化加权经济分数
- 准确给出每个区划的邻接值与邻接分解

本题重点区划为：
- `HARBOR`
- `COMMERCIAL_HUB`
- `CANAL`
- `AQUEDUCT`
- `INDUSTRIAL_ZONE`

## 输入

`/data/coastal_corridor/scenario.json` 提供：
- `map_file`: 原始 `.Civ6Map`
- `population`: 城市人口
- `candidate_city_centers`: 可选城市中心坐标
- `district_pool`: 必须完整放置的一组区划
- `score_weights`: 加权经济分数的权重

仍然需要遵守标准 Civ6 规则，包括但不限于：
- 城市中心必须落在合法陆地
- 所有区划必须在城市中心 3 格内
- `HARBOR` 必须在临陆海岸或湖泊
- `COMMERCIAL_HUB` 的河流加成必须正确判断
- `AQUEDUCT` 必须同时满足城市中心相邻与淡水条件
- `CANAL` 必须真正连通城市中心/水体或两片分离水体
- 区划不可重叠，且特色区划数量不能超过人口上限

## 输出

将结果写入：
- `/output/coastal_corridor_plan.json`

输出格式必须是：

```json
{
  "city_center": [x, y],
  "placements": {
    "HARBOR": [x, y],
    "COMMERCIAL_HUB": [x, y],
    "CANAL": [x, y],
    "AQUEDUCT": [x, y],
    "INDUSTRIAL_ZONE": [x, y]
  },
  "adjacency_bonuses": {
    "HARBOR": 2,
    "COMMERCIAL_HUB": 5,
    "CANAL": 0,
    "AQUEDUCT": 0,
    "INDUSTRIAL_ZONE": 4
  },
  "adjacency_breakdowns": {
    "HARBOR": {
      "CITY_CENTER": {
        "count": 1,
        "bonus": 2,
        "bonus_per": 2,
        "count_required": 1,
        "sources": ["CITY_CENTER@(x,y)"]
      }
    },
    "COMMERCIAL_HUB": {
      "RIVER": {
        "count": 1,
        "bonus": 2,
        "sources": ["OnRiver"]
      }
    },
    "CANAL": {},
    "AQUEDUCT": {},
    "INDUSTRIAL_ZONE": {
      "AQUEDUCT+BATH+DAM+CANAL": {
        "count": 2,
        "bonus": 4,
        "bonus_per": 2,
        "count_required": 1,
        "sources": ["AQUEDUCT@(x,y)", "CANAL@(x,y)"]
      }
    }
  },
  "total_adjacency": 11,
  "weighted_score": 41
}
```

## 计分

加权经济分数定义为：

`4 * HARBOR + 5 * COMMERCIAL_HUB + 3 * INDUSTRIAL_ZONE`

这里的 `HARBOR`、`COMMERCIAL_HUB`、`INDUSTRIAL_ZONE` 指对应区划的邻接值。

要求：
1. `placements` 的键必须与 `district_pool` 完全一致，不能缺失也不能增加。
2. `adjacency_bonuses` 必须逐区划准确。
3. `adjacency_breakdowns` 必须准确反映每个区划的邻接来源；若某区划没有邻接，则填 `{}`。
4. `total_adjacency` 必须等于所有区划邻接值之和。
5. `weighted_score` 必须与上面的公式严格一致。

评分规则：
- 任一格式、合法性或邻接计算错误：得分为 `0`
- 否则：`your_weighted_score / optimal_weighted_score`，上限为 `1.0`

存在多种合法方案时，只有达到最优加权分数的方案才能拿到满分。
