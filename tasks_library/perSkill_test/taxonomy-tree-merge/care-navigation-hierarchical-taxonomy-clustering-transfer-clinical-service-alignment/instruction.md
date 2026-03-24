你要把三套临床服务目录路径统一成一套 5 层 clinical service taxonomy，供后续做预约导航、服务线报表和跨机构需求分析。

输入数据都在 `/root/data/`：

- `hospital_group_services.csv`
  - 列：`enterprise_service_line`, `hospital_service_code`, `booking_surface`, `care_mode`
  - 路径分隔符已经是 ` > `
- `payer_benefit_catalog.jsonl`
  - 字段：`benefit_hierarchy`, `benefit_code`, `entry_point`, `setting`
  - 路径分隔符是 ` / `
- `telehealth_visit_directory.tsv`
  - 列：`visit_tree`, `visit_id`, `intake_channel`, `modality`
  - 路径分隔符是 ` :: `

你的目标：

1. 读取三份输入，并把不同分隔符统一成 ` > `。
2. 标准化服务节点文本，尽量消除大小写、连字符、`&`、缩写和近义表达差异。
3. 把语义相近的临床服务路径对齐到同一套 5 层服务 taxonomy 中，让医院、保险和远程医疗里的等价服务尽量落到同一统一路径。
4. 生成一份预约导航摘要，显示每个统一服务叶子覆盖了几个来源系统、多少种入口，以及不同 care mode 的分布。

请遵守这些规则：

1. 输出必须是固定 5 层结构，顶层控制在 7-10 个 broad clinical service lines。
2. 统一服务名称使用 ` | ` 连接关键词，总词数不超过 5。
3. 子类名称不要只是父类名称的重复。
4. 同一个统一服务节点下要尽量混合不同 source system，不要按医院、保险或平台拆树。
5. 统一 taxonomy 名称里不要出现机构名、渠道品牌名，也不要残留原始分隔符。
6. 输出中的原始路径列必须使用统一后的 ` > ` 分隔符。
7. `care_mode` 只允许使用 `in_person`、`virtual`、`hybrid`、`ancillary` 四类。

把结果写到 `/root/output/` 下三个文件：

1. `clinical_service_crosswalk.csv`
   - `source_system`
   - `source_service_id`
   - `source_service_path`
   - `normalized_service_path`
   - `source_depth`
   - `booking_surface`
   - `care_mode`
   - `unified_service_l1`
   - `unified_service_l2`
   - `unified_service_l3`
   - `unified_service_l4`
   - `unified_service_l5`

2. `clinical_taxonomy_hierarchy.csv`
   - `unified_service_l1`
   - `unified_service_l2`
   - `unified_service_l3`
   - `unified_service_l4`
   - `unified_service_l5`

3. `care_navigation_summary.csv`
   - `unified_service_l1`
   - `unified_service_l2`
   - `unified_service_l3`
   - `unified_service_l4`
   - `unified_service_l5`
   - `source_system_count`
   - `booking_surface_count`
   - `in_person_count`
   - `virtual_count`
   - `hybrid_count`
   - `ancillary_count`

验收重点：

- 三个 source system 的记录都要保留。
- `Same-Day Care`、`Same-Day Video`、`On-Demand Visits` 这类低急症即时就诊应尽量对齐。
- `Routine Obstetrics`、`Prenatal Routine`、`Trimester Visit` 这类产科常规产检应尽量归到同一统一路径。
- `Knee Arthroplasty`、`Knee Replacement`、`Surgical Pathways` 这类膝关节置换服务应能对齐。
- 生成的统一服务树要适合真实预约导航，而不是仅仅把原字符串做轻微改名。
