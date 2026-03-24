你要把三套公共服务工单问题路径统一成一套 4 层 service request taxonomy，供后续做跨系统派单统计、热点问题聚合和 SLA 监控。

输入数据都在 `/root/data/`：

- `city311_service_requests.csv`
  - 列：`sr_id`, `complaint_hierarchy`, `submission_channel`, `district`, `priority_code`, `sla_target_hours`
  - 路径分隔符已经是 ` > `
- `campus_maintenance_queue.jsonl`
  - 字段：`ticket_ref`, `issue_tree`, `request_channel`, `campus_zone`, `urgency_code`, `target_hours`
  - 路径分隔符是 ` / `
- `residential_portfolio_work_orders.xlsx`
  - 列：`work_order_no`, `problem_path`, `resident_touchpoint`, `portfolio_cluster`, `service_level`, `due_within_hours`
  - 路径分隔符是 ` :: `

你的目标：

1. 读取三份输入，并把不同分隔符统一成 ` > `。
2. 标准化问题节点文本、渠道字段和优先级字段，尽量消除大小写、连字符、近义表达和系统内缩写差异。
3. 把语义相近的问题路径对齐到同一套 4 层服务请求 taxonomy 中，让城市 311、校园后勤和物业里的等价问题尽量落到同一统一路径。
4. 生成一份按统一问题叶子汇总的派单与 SLA 统计，用于识别热点问题和高时效风险类目。

请遵守这些规则：

1. 输出必须是固定 4 层结构，顶层控制在 5-8 个 broad service domains。
2. 统一分类名称使用 ` | ` 连接关键词，总词数不超过 5。
3. 子类名称不要只是父类名称的重复。
4. 同一个统一问题节点下要尽量混合不同 source system，不要按城市、校园或物业拆树。
5. 统一 taxonomy 名称里不要出现城市名、校园名、物业品牌名，也不要残留原始分隔符。
6. 输出中的 `source_issue_path` 必须使用统一后的 ` > ` 分隔符。
7. `priority_band` 只允许使用 `emergency`、`urgent`、`routine` 三类。
8. `intake_channel` 要归一成少量稳定值，例如 `phone`、`web`、`mobile_app`、`email`、`resident_portal`、`front_desk` 这类可汇总形式。

把结果写到 `/root/output/` 下三个文件：

1. `service_request_crosswalk.csv`
   - `source_system`
   - `request_id`
   - `source_issue_path`
   - `normalized_issue_path`
   - `source_depth`
   - `intake_channel`
   - `priority_band`
   - `sla_target_hours`
   - `unified_issue_l1`
   - `unified_issue_l2`
   - `unified_issue_l3`
   - `unified_issue_l4`

2. `service_request_taxonomy_hierarchy.csv`
   - `unified_issue_l1`
   - `unified_issue_l2`
   - `unified_issue_l3`
   - `unified_issue_l4`

3. `dispatch_sla_rollup.csv`
   - `unified_issue_l1`
   - `unified_issue_l2`
   - `unified_issue_l3`
   - `unified_issue_l4`
   - `request_count`
   - `source_system_count`
   - `intake_channel_count`
   - `emergency_count`
   - `urgent_count`
   - `routine_count`
   - `median_sla_target_hours`
   - `max_sla_target_hours`

验收重点：

- 三个 source system 的记录都要保留。
- `Graffiti`、`Wall Markings`、`Hallway Wall` 这类涂鸦清理请求应尽量对齐。
- `Service Outage`、`Stalled Car`、`Elevator Offline`、`Lift Outage` 这类电梯停运问题应能归到同一统一路径。
- `Active Leak`、`Burst Pipe`、`Hallway Drip` 这类漏水问题应能对齐，并在 SLA 汇总里体现为高优先级热点。
- `Cooling Outage`、`Air Conditioner Failure`、`Condenser Fault` 这类空调失冷问题应能对齐。
- 生成的统一问题树要适合派单统计和热点监控，而不是仅仅把原字符串做轻微改名。
