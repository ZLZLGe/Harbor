## 任务说明

请读取以下 3 个输入文件，并覆盖 `/app/workspace/` 根目录中已经放好的目标工作簿文件；目标文件主文件名为 `volunteer_shift_plan`：

- `/app/workspace/data/volunteers.tsv`
- `/app/workspace/data/shift_needs.csv`
- `/app/workspace/data/availability.json`

输出工作簿必须且只能包含以下 4 个工作表，名称与顺序都要一致：

1. `班次需求`
2. `分配结果`
3. `人员负载`
4. `缺口概览`

### 排班规则

- `volunteers.tsv` 按文件顺序给出志愿者基础信息，字段为：
  - `volunteer_id`
  - `volunteer_name`
  - `team`
  - `eligible_roles`
  - `max_shifts`
- `eligible_roles` 使用 `|` 分隔，表示该志愿者可以承担的岗位
- `shift_needs.csv` 按文件顺序给出班次需求，字段为：
  - `shift_id`
  - `shift_date`
  - `start_time`
  - `end_time`
  - `site`
  - `role`
  - `required_count`
- `availability.json` 中每个志愿者对应一个 `available_shifts` 列表
- 处理班次时必须严格按照 `shift_needs.csv` 的行顺序
- 对某个班次，候选志愿者必须同时满足：
  - 该班次在他的 `available_shifts` 中
  - 班次 `role` 出现在他的 `eligible_roles` 中
  - 当前已分配班次数严格小于 `max_shifts`
  - 与他已分配的其他班次不存在时间重叠
- 时间重叠定义：同一天内，`start_time < 已分配班次的 end_time` 且 `end_time > 已分配班次的 start_time`
- 每个班次的候选人按以下顺序排序后取前 `required_count` 人：
  - 当前已分配班次数从少到多
  - 在 `volunteers.tsv` 中出现得更早的优先
- 如果候选人不足，就只分配实际可用人数，剩余缺口保留为空缺

### 工作表要求

#### 1. `班次需求`

- 第一行必须是表头
- 列严格为：
  - `shift_id`
  - `shift_date`
  - `start_time`
  - `end_time`
  - `site`
  - `role`
  - `required_count`
  - `assigned_count`
  - `gap_count`
- 前 7 列按 `shift_needs.csv` 原始顺序逐行写入
- `shift_date` 必须写成真正的日期单元格
- `start_time`、`end_time` 必须写成真正的时间单元格
- `assigned_count` 和 `gap_count` 必须使用工作表公式，不能直接写成常量

#### 2. `分配结果`

- 第一行必须是表头
- 列严格为：
  - `shift_id`
  - `shift_date`
  - `start_time`
  - `end_time`
  - `site`
  - `role`
  - `volunteer_id`
  - `volunteer_name`
  - `team`
  - `load_after_assignment`
  - `overlap_flag`
- 每个已分配的志愿者占一行
- 行顺序必须与实际分配顺序一致：先按班次顺序，再按该班次内的候选排序结果
- `shift_date` 必须写成真正的日期单元格
- `start_time`、`end_time` 必须写成真正的时间单元格
- `load_after_assignment` 必须使用工作表公式，表示该志愿者截至当前行累计被分配了多少个班次
- `overlap_flag` 必须使用工作表公式；如果同一志愿者在同一天存在时间重叠的已分配班次则写 `冲突`，否则留空

#### 3. `人员负载`

- 第一行必须是表头
- 列严格为：
  - `volunteer_id`
  - `volunteer_name`
  - `team`
  - `max_shifts`
  - `assigned_shifts`
  - `remaining_capacity`
  - `conflict_flag`
- 行顺序必须与 `volunteers.tsv` 一致
- 前 4 列来自 `volunteers.tsv`
- `assigned_shifts`、`remaining_capacity`、`conflict_flag` 都必须使用工作表公式
- `conflict_flag` 规则：
  - 该志愿者在 `分配结果` 中任意一行 `overlap_flag` 为 `冲突` 时写 `冲突`
  - 否则留空

#### 4. `缺口概览`

- 第一行必须是表头，列严格为 `metric`、`value`
- 数据行顺序固定为：
  - `total_required`
  - `total_assigned`
  - `total_gap`
  - `filled_shift_count`
  - `unfilled_shift_count`
  - `volunteers_used`
  - `conflicted_assignment_rows`
- `value` 列必须全部使用工作表公式

不要生成额外工作表、额外列、说明区或辅助区域。
