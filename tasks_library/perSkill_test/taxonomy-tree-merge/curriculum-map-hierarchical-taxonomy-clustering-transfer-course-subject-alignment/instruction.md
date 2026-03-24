你要把三所大学的课程目录路径统一成一套 4 层学科 taxonomy，供后续做跨校转学分分析、课程覆盖统计和培养方案对照。

输入数据都在 `/root/data/`：

- `northbridge_course_catalog.csv`
  - 列：`catalog_path`, `course_code`, `course_title`, `credits`
  - 路径分隔符已经是 ` > `
- `redwood_school_catalog.jsonl`
  - 字段：`academic_path`, `course_id`, `title`, `units`
  - 路径分隔符是 ` / `
- `lakeside_program_catalog.tsv`
  - 列：`curriculum_branch`, `catalog_number`, `course_name`, `credit_hours`
  - 路径分隔符是 ` :: `

你的目标：

1. 读取三份输入，并把不同分隔符统一成 ` > `。
2. 标准化课程标题和学科节点文本，尽量消除大小写、连字符、数字写法和近义表达差异。
3. 把语义相近的课程路径对齐到同一套 4 层学科 taxonomy 中，让跨校等价课程尽量落到同一统一路径。
4. 生成一份转学分对齐摘要，用来显示每个统一学科叶子下覆盖了几所学校、几门课程，以及学分区间。

请遵守这些规则：

1. 输出必须是固定 4 层结构，顶层控制在 6-9 个 broad subject areas。
2. 统一学科名称使用 ` | ` 连接关键词，总词数不超过 5。
3. 子类名称不要只是父类名称的重复。
4. 同一个统一学科节点下要尽量混合不同 university，不要按学校拆树。
5. 课程名称、统一 taxonomy 名称和等价组标识里都不要出现学校名。
6. 输出中的课程路径列要使用统一后的 ` > ` 分隔符。
7. 等价组标识使用小写 snake_case，语义上应能代表该组课程。

把结果写到 `/root/output/` 下三个文件：

1. `course_transfer_mapping.csv`
   - `university`
   - `course_code`
   - `course_title`
   - `source_course_path`
   - `credit_units`
   - `source_depth`
   - `normalized_course_title`
   - `equivalency_group`
   - `subject_area_l1`
   - `subject_area_l2`
   - `subject_area_l3`
   - `subject_area_l4`

2. `subject_taxonomy_hierarchy.csv`
   - `subject_area_l1`
   - `subject_area_l2`
   - `subject_area_l3`
   - `subject_area_l4`

3. `transfer_overlap_summary.csv`
   - `equivalency_group`
   - `subject_area_l1`
   - `subject_area_l2`
   - `subject_area_l3`
   - `subject_area_l4`
   - `university_count`
   - `course_count`
   - `min_credit_units`
   - `max_credit_units`

验收重点：

- 三所大学的课程都要保留。
- `Introduction to Programming`、`Programming Fundamentals`、`Intro to Coding` 这类等价课程，应该被归到同一统一学科路径。
- `Calculus I`、`General Chemistry I`、`Principles of Microeconomics` 这类跨校基础课也应尽量对齐。
- 统一后的学科树应该适合转学分与培养方案对照，而不是仅仅把原字符串做轻微改名。
