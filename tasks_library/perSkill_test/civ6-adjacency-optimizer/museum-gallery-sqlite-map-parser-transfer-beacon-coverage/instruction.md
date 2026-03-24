# 博物馆重点展品语音导览信标部署

你需要根据一个博物馆展厅楼层数据库，给出房间级导览信标部署方案，而不是做一般性的场馆摘要。

## 输入

读取：
- `/data/briefing/beacon_request.json`

其中会给出：
- `layout_db`: 楼层数据库路径
- `priority_tiers`: 需要被导览信标覆盖的展品优先级
- `required_voltage`: 可用于安装信标的供电电压
- `max_room_hops`: 单个信标可跨越的最大房间跳数
- `shortlist_size`: 候选安装点最多输出多少个

## 目标

从 SQLite 数据库中恢复：
- 展厅房间列表及排序
- 访客可通行的门连接关系
- 展品所在房间与优先级
- 供电点、安装点及其可用状态

然后选出一组最小化的信标安装点，使所有重点展品都被覆盖，并把结果写到：
- `/output/gallery_beacon_plan.json`

## 有效安装点

某个安装点只有同时满足以下条件，才算有效：

1. 安装点未被封挡。
2. 安装点关联的供电点处于通电状态。
3. 供电点电压等于 `required_voltage`。

## 覆盖规则

1. 只考虑 `priority_tiers` 中的重点展品。
2. 一个信标会覆盖其所在房间，以及从该房间出发，仅沿 `visitor_access = 1` 的门连接，最短路径不超过 `max_room_hops` 的所有房间。
3. 如果重点展品所在房间被某个信标覆盖，则该展品视为已覆盖。

## 选点规则

在所有有效安装点中，选择一个部署方案，排序目标依次为：

1. 使用的信标数量更少
2. `install_cost` 总和更低
3. 选中安装点的 `mount_code` 升序列表字典序更小

## 候选位排序

输出 `candidate_beacons` 时，对所有有效安装点按以下规则排序：

1. `covered_priority_count` 更大者优先
2. `install_cost` 更低者优先
3. `mount_code` 更小者优先

只保留前 `shortlist_size` 个。

## 输出格式

请严格输出如下结构：

```json
{
  "gallery": {
    "venue_name": "Harbor Museum of Modern Objects",
    "exhibition_name": "Cities in Motion",
    "room_count": 7,
    "visitor_door_count": 6
  },
  "rules": {
    "priority_tiers": ["A", "B"],
    "required_voltage": 24,
    "max_room_hops": 1,
    "shortlist_size": 4
  },
  "summary": {
    "priority_exhibits": 5,
    "valid_mount_points": 5,
    "selected_beacons": 2,
    "priority_rooms_covered": 5
  },
  "priority_exhibits": [
    {
      "exhibit_code": "EXH_BRONZE",
      "title": "Bronze Routes",
      "tier": "A",
      "room_code": "GAL_A",
      "room_name": "Impression Hall"
    }
  ],
  "candidate_beacons": [
    {
      "mount_code": "MP_SCULPT_01",
      "mount_label": "Central truss",
      "room_code": "SCULPT",
      "room_name": "Sculpture Court",
      "feed_code": "PF_SCULPT_A",
      "install_cost": 4,
      "coverage_rooms": ["ARCHIVE", "GAL_A", "SCULPT"],
      "covered_exhibits": ["EXH_BRONZE", "EXH_MARBLE", "EXH_SCROLL"],
      "covered_priority_count": 3
    }
  ],
  "deployment_plan": {
    "selected_mount_codes": ["MP_MEDIA_01", "MP_SCULPT_01"],
    "total_install_cost": 9,
    "beacons": [
      {
        "mount_code": "MP_MEDIA_01",
        "mount_label": "Acoustic rail",
        "room_code": "MEDIA",
        "room_name": "Media Lab",
        "feed_code": "PF_MEDIA_A",
        "install_cost": 5,
        "coverage_rooms": ["GAL_B", "LOUNGE", "MEDIA"],
        "covered_exhibits": ["EXH_SOUND", "EXH_TRANSIT"]
      }
    ],
    "coverage_assignments": [
      {
        "exhibit_code": "EXH_BRONZE",
        "mount_code": "MP_SCULPT_01"
      }
    ]
  }
}
```

## 要求

1. JSON 必须合法。
2. 所有房间、门连接、展品、供电点和安装点都必须与数据库内容一致。
3. `priority_exhibits` 必须按 `exhibit_code` 升序输出。
4. `candidate_beacons` 必须已经按题目要求排序，并且长度不超过 `shortlist_size`。
5. `deployment_plan.selected_mount_codes` 必须与最终部署方案一致，且按升序输出。
6. `coverage_assignments` 必须覆盖全部重点展品，并按 `exhibit_code` 升序输出。
