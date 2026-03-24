请读取 `/root/data/dam_watch_station_candidates.tsv`。文件中给出了水库运行值守候选测站清单，每条记录包含：
- `reservoir_id`
- `station_id`
- `watch_tier`
- `audit_note`

请对清单中的每个 `station_id` 拉取 USGS 站点元数据，并执行一次候选测站审计。只保留同时满足以下条件的记录：
- 属于河流测站
- 具有非空的站点名称
- 具有非空的纬度
- 具有非空的经度
- 具有非空的州代码
- 具有非空的排水面积

将通过审计的记录写入 `/root/output/station_metadata_audit.json`。输出必须是一个 JSON 数组，数组中的每个对象只包含以下字段：
- `station_id`
- `site_name`
- `state`
- `latitude`
- `longitude`
- `drainage_area_sqmi`

其中：
- `state` 请保留站点元数据中的州代码
- `latitude` 和 `longitude` 保留 6 位小数
- `drainage_area_sqmi` 保留 3 位小数

请按以下顺序排序输出：
1. `state` 升序
2. `station_id` 升序
