# 湿地关键栖息点监测传感器布设

你需要根据一个湿地保护区布局数据库，给出监测传感器布设方案，而不是做一般性的生态摘要。

## 输入

读取：
- `/data/briefing/sensor_request.json`

其中会给出：
- `layout_db`: 湿地布局数据库路径
- `target_habitat_types`: 需要重点覆盖的栖息地类型
- `priority_weights`: 各优先级对应的权重
- `blocked_overlay_codes`: 视为禁入或封闭的覆盖标记
- `sensor_radius`: 传感器可覆盖关键栖息点的最大曼哈顿距离
- `min_bank_contacts`: 合法安装点至少需要接触多少个水道相邻格
- `budget_cap`: 总预算上限
- `max_sites`: 最多允许安装多少个传感器点位
- `shortlist_size`: 候选位最多输出多少个

## 目标

从 SQLite 数据库中恢复：
- 保护区网格尺寸
- 每个地块的线性编码与 `(x, y)` 坐标
- 水道覆盖地块
- 栖息地标签与优先级
- 禁入区覆盖标记
- 传感器候选安装点及成本

然后筛选出合法候选位，并在预算限制下选出一组传感器点位，把结果写到：
- `/output/sensor_siting_plan.json`

## 合法候选位

某个候选安装点只有同时满足以下条件，才算有效：

1. 对应地块 `installable = 1`。
2. 对应地块没有 `blocked_overlay_codes` 中的覆盖标记。
3. 对应地块本身不是重点栖息地地块。
4. 该地块与其四联通相邻地块中，带有水道标记的地块数量至少为 `min_bank_contacts`。

## 覆盖规则

1. 只考虑 `target_habitat_types` 中的重点栖息地。
2. 如果某个重点栖息地点与传感器安装点的曼哈顿距离不超过 `sensor_radius`，则该栖息点视为被该传感器覆盖。
3. 同一个栖息点被多个传感器覆盖时，只按一次计入总覆盖。

## 候选位排序

输出 `candidate_sites` 时，对所有合法候选位按以下规则排序：

1. `coverable_priority_weight` 更高者优先
2. `coverable_habitat_count` 更高者优先
3. `install_cost` 更低者优先
4. `bank_contacts` 更高者优先
5. `site_code` 更小者优先

只保留前 `shortlist_size` 个。

## 最终部署方案

在所有合法候选位中，选择一个满足 `budget_cap` 且传感器数量不超过 `max_sites` 的部署方案，排序目标依次为：

1. `covered_priority_weight` 更高
2. `covered_habitats` 数量更多
3. `total_install_cost` 更低
4. `selected_site_codes` 升序列表的字典序更小

## 输出格式

请严格输出如下结构：

```json
{
  "reserve": {
    "reserve_name": "Lotus Marsh Wetland Reserve",
    "width": 7,
    "height": 6,
    "cell_size_m": 50
  },
  "rules": {
    "target_habitat_types": ["TERN_NEST", "OTTER_DEN"],
    "sensor_radius": 2,
    "min_bank_contacts": 1,
    "budget_cap": 13,
    "max_sites": 3,
    "shortlist_size": 5
  },
  "summary": {
    "waterway_parcels": 13,
    "key_habitats": 8,
    "candidate_sites": 7,
    "shortlisted_sites": 5,
    "selected_sites": 3,
    "covered_habitats": 7,
    "covered_priority_weight": 23,
    "budget_used": 13
  },
  "key_habitats": [
    {
      "habitat_code": "HAB_TERN_01",
      "parcel_id": 8,
      "x": 1,
      "y": 1,
      "label": "North rookery",
      "habitat_type": "TERN_NEST",
      "priority_tier": "critical",
      "priority_weight": 5,
      "waterway_contacts": 2
    }
  ],
  "no_entry_zones": [
    {
      "parcel_id": 4,
      "x": 4,
      "y": 0,
      "overlay_codes": ["NO_ENTRY"]
    }
  ],
  "candidate_sites": [
    {
      "site_code": "SEN_PAD_B",
      "site_label": "Central observation rail",
      "parcel_id": 17,
      "x": 3,
      "y": 2,
      "access_code": "OBS_PLATFORM",
      "install_cost": 6,
      "bank_contacts": 1,
      "coverable_habitat_codes": ["HAB_OTTER_03", "HAB_OTTER_06"],
      "coverable_habitat_count": 4,
      "coverable_priority_weight": 14
    }
  ],
  "deployment_plan": {
    "selected_site_codes": ["SEN_PAD_A", "SEN_PAD_B", "SEN_PAD_F"],
    "total_install_cost": 13,
    "covered_habitat_codes": ["HAB_OTTER_03", "HAB_TERN_01"],
    "uncovered_habitat_codes": ["HAB_TERN_07"],
    "sensors": [
      {
        "site_code": "SEN_PAD_A",
        "site_label": "Willow boardwalk spur",
        "parcel_id": 15,
        "x": 1,
        "y": 2,
        "install_cost": 4,
        "bank_contacts": 2,
        "covered_habitat_codes": ["HAB_REED_02", "HAB_REED_05", "HAB_TERN_01"]
      }
    ]
  }
}
```

## 要求

1. JSON 必须合法。
2. `parcel_id` 与 `(x, y)` 的还原必须正确。
3. `key_habitats` 必须按 `habitat_code` 升序输出。
4. `no_entry_zones` 必须按 `parcel_id` 升序输出。
5. `candidate_sites` 必须已经按题目规则排序，并且长度不超过 `shortlist_size`。
6. `deployment_plan.selected_site_codes` 必须按升序输出。
7. `summary` 中的覆盖数量、权重和预算消耗必须与部署方案一致。
