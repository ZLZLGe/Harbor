# Telemetry Incident Rollups Transfer

请修复并完成 `/root/TelemetryIncidentRollups.scala`。当前文件是一份故意不完整的 Scala 2.13 端口，你需要以 `/root/telemetry_incident_rollups.py` 为语义参考，把它补成可运行且结果一致的版本。

实现要求：

- 不要写 `package` 声明。
- 只使用 Scala 2.13 标准库，不要引入第三方依赖。
- 输出文件必须定义公开对象 `TelemetryIncidentRollups`。
- `TelemetryIncidentRollups` 内必须提供这些公开数据结构：
  - `AlertRecord(service, severity, startedAt, endedAt, source, alertCode)`
  - `WindowRule(mergeGapMinutes, pageThreshold, summaryPrefix)`
  - `WindowConfig(defaultMergeGapMinutes, severityRank, rulesByService)`
  - `IncidentSummary(service, severity, startedAt, endedAt, durationMinutes, alertCount, sourceCount, sources, alertCodes, page, summary)`
- `TelemetryIncidentRollups` 内必须提供这些公开函数：
  - `loadAlerts(path: String)`
  - `loadWindowConfig(path: String)`
  - `rollupIncidents(alerts, config)`
  - `buildServiceDigest(incidents, severityRank)`
  - `renderIncidentLines(incidents)`

输入资产：

- `/root/alerts.csv`
- `/root/window_rules.conf`
- `/root/telemetry_incident_rollups.py`
- `/root/TelemetryIncidentRollups.scala`

输入规则：

- `alerts.csv` 按表头读取，字段固定为：
  - `service`
  - `severity`
  - `started_at`
  - `ended_at`
  - `source`
  - `alert_code`
- 所有文本字段都先 `trim`。
- `service`、`severity`、`source` 统一转成小写。
- `alert_code` 统一转成大写。
- 时间字符串使用 UTC ISO 格式：`YYYY-MM-DDTHH:MM:SSZ`。
- `window_rules.conf` 是简单的 INI 风格文本：
  - 空行忽略。
  - 以 `#` 开头的行忽略。
  - 顶层键至少包含 `default_merge_gap_minutes` 与 `severity_rank`。
  - `[service-name]` 表示某个服务的 section。
  - section 中会提供 `merge_gap_minutes`、`page_threshold`、`summary_prefix`。

语义契约：

- `loadWindowConfig` 需要返回：
  - `defaultMergeGapMinutes`
  - `severityRank`
  - `rulesByService`
- 当某个服务没有专属 section 时，`rollupIncidents` 必须使用这些默认值：
  - `mergeGapMinutes = defaultMergeGapMinutes`
  - `pageThreshold = 2`
  - `summaryPrefix = "observe"`
- `rollupIncidents` 必须先按 `(service, severity)` 分桶，再在每个桶内按以下顺序排序：
  - `startedAt` 升序
  - `endedAt` 升序
  - `source` 升序
  - `alertCode` 升序
- 同一桶内，相邻两条告警满足下面条件时必须合并到同一个 incident：
  - `next.startedAt <= currentEndedAt + mergeGapMinutes`
- 合并后的 incident 字段规则：
  - `startedAt` 取该 incident 的最早开始时间，输出时仍用原始 ISO 字符串格式
  - `endedAt` 取该 incident 的最晚结束时间，输出时仍用原始 ISO 字符串格式
  - `durationMinutes` 是 `endedAt - startedAt` 的整分钟数
  - `alertCount` 是被合并进来的告警条数
  - `sources` 是去重后按字典序排序的来源列表
  - `sourceCount` 是 `sources.size`
  - `alertCodes` 是去重后按字典序排序的告警编码列表
  - `page` 为真当且仅当：
    - `severity == "critical"`，或
    - `sourceCount >= pageThreshold`
  - `summary` 必须严格使用这个格式：
    - `<summaryPrefix>|<service>|<severity>|<startedAt>|<endedAt>|<source1,source2,...>|<code1,code2,...>|<alertCount>`
    - 当来源列表或编码列表为空时，对应位置输出 `-`
- `rollupIncidents` 返回的 incident 列表必须整体按以下顺序排序：
  - `service` 升序
  - `severity` 按 `severityRank` 给出的顺序；不在 `severityRank` 中的值排在后面，并按字典序升序
  - `startedAt` 升序
  - `endedAt` 升序
- `renderIncidentLines` 必须按传入顺序返回文本行，每行格式严格为：
  - `INCIDENT|<service>|<severity>|<startedAt>|<endedAt>|<durationMinutes>|<alertCount>|<sourceCount>|<source1,source2,...>|<code1,code2,...>|<page>|<summary>`
  - 当来源列表或编码列表为空时，对应位置输出 `-`
- `buildServiceDigest` 必须返回服务级摘要文本行，每行格式严格为：
  - `SERVICE|<service>|<incidentCount>|<pagedCount>|<severity1:count1,severity2:count2,...>|<source1,source2,...>`
- `buildServiceDigest` 的统计规则：
  - `incidentCount` 是该服务 incident 数量
  - `pagedCount` 是该服务 `page == true` 的 incident 数量
  - 严重级别分布只保留实际出现过的级别，顺序先按 `severityRank`，再附加不在 `severityRank` 中的级别并按字典序升序
  - 服务来源列表取该服务所有 incident 的 `sources` 并集，去重后按字典序排序
- `buildServiceDigest` 返回行的排序规则：
  - `pagedCount` 降序
  - `incidentCount` 降序
  - `service` 升序

修复要求：

- 题目提供的 `/root/TelemetryIncidentRollups.scala` 当前带有占位实现，你需要在原路径补全它。
- 可以重写原文件，但最终必须满足上述公开接口和输出契约。

验证方式：

- 测试会直接编译 `/root/TelemetryIncidentRollups.scala`。
- 测试会同时使用题目给定的输入资产和临时构造的新告警/配置文件。
- 测试会把 Scala 输出的 incident 行与服务摘要行和 Python 参考实现逐项比对。
- 只要公开接口、排序和可观察结果一致，内部实现细节不限。
