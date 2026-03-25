# Shift Coverage Planner Transfer

请把 `/root/shift_coverage_planner.py` 翻译为 Scala 2.13，并把最终代码写到 `/root/ShiftCoveragePlanner.scala`。

实现要求：

- 不要写 `package` 声明。
- 只使用 Scala 2.13 标准库，不要引入第三方依赖。
- 输出文件必须定义公开对象 `ShiftCoveragePlanner`。
- `ShiftCoveragePlanner` 内必须提供这些公开数据结构：
  - `ShiftNeed(date, slot, role, requiredStaff)`
  - `EmployeeSkill(employeeId, roles, preferredSlots, unavailableDates)`
  - `LeavePreference(employeeId, date, avoidSlots, priority, note)`
  - `CoverageGap(date, slot, role, requiredStaff, assignedEmployees, missingCount)`
  - `EmployeeConflict(employeeId, date, slot, roles)`
  - `SwapSuggestion(date, slot, role, fromEmployee, toEmployee, score, reasons)`
  - `PlanningResult(gaps, conflicts, suggestions)`
- `ShiftCoveragePlanner` 内必须提供这些公开函数：
  - `loadShiftNeeds(path: String)`
  - `loadEmployeeSkills(path: String)`
  - `loadLeavePreferences(path: String)`
  - `planCoverage(shiftNeeds, employeeSkills, leavePreferences)`
  - `renderPlan(result)`
  - `writePlan(result, outputPath: String)`
- `ShiftCoveragePlanner` 必须提供可运行的 `main(args: Array[String]): Unit`，并按下面的命令行契约工作：
  - `args(0)` 是班次需求 CSV 路径
  - `args(1)` 是员工技能 CSV 路径
  - `args(2)` 是请假偏好 CSV 路径
  - `args(3)` 是输出计划文件路径
  - 参数数量不为 4 时，应输出用法信息并以非 0 状态退出

输入资产：

- `/root/shift_requirements.csv`
- `/root/employee_skills.csv`
- `/root/leave_preferences.csv`
- `/root/shift_coverage_planner.py`

输入规则：

- 三个 CSV 都按表头读取。
- 所有文本字段都要先 `trim`。
- `slot`、`role`、`roles`、`preferred_slots`、`avoid_slots` 都按小写处理。
- `roles`、`preferred_slots`、`unavailable_dates`、`avoid_slots` 都使用 `|` 分隔；空项要忽略。
- `avoid_slots` 中的 `all` 表示整天都应避免排班。
- 允许同一个员工同一天出现多条请假偏好；匹配某个班次时，取所有匹配记录中的最大 `priority`。

排班语义契约：

- `loadShiftNeeds` 读取字段：
  - `date`
  - `slot`
  - `role`
  - `required_staff`
- `loadEmployeeSkills` 读取字段：
  - `employee_id`
  - `roles`
  - `preferred_slots`
  - `unavailable_dates`
- `loadLeavePreferences` 读取字段：
  - `employee_id`
  - `date`
  - `avoid_slots`
  - `priority`
  - `note`

- `planCoverage` 必须先对每个 `(date, slot, role)` 独立生成一份“基线分配”，不要在这一步提前消解跨岗位冲突。
- 某员工能进入某班次岗位的候选集，当且仅当：
  - 该员工具备对应 `role`
  - 该 `date` 不在员工的 `unavailableDates` 里
- 基线分配的候选人排序规则必须严格为：
  - 没有匹配到该 `date + slot` 请假偏好的员工在前
  - 偏好当前 `slot` 的员工在前
  - `roles.size` 更小的员工在前
  - `employeeId` 升序
- 基线分配对每个岗位直接取排序后的前 `requiredStaff` 名员工，即使这些员工已经在同一 `date + slot` 的其他岗位上被选中过，也不能在这一步排除。

- `CoverageGap` 规则：
  - `assignedEmployees` 保留该岗位基线分配到的员工列表顺序
  - `missingCount = requiredStaff - assignedEmployees.size`
  - 只保留 `missingCount > 0` 的岗位
  - gap 列表排序规则为 `date`、`slot`、`role` 升序

- `EmployeeConflict` 规则：
  - 如果同一员工在同一个 `date + slot` 被基线分配到多个不同 `role`，就形成一条冲突
  - `roles` 需要去重后按字典序排序
  - conflict 列表排序规则为 `date`、`slot`、`employeeId` 升序

- `SwapSuggestion` 规则：
  - 只对“有冲突”或“命中请假偏好”的已分配员工生成候选换班建议
  - 对于某条已分配记录 `(date, slot, role, fromEmployee)`，可替换员工必须同时满足：
    - 具备该 `role`
    - 该 `date` 不在其 `unavailableDates` 里
    - 没有被基线分配到同一个 `date + slot` 的任何岗位
    - 对该 `date + slot` 没有匹配到请假偏好
  - 可替换员工的排序规则必须严格为：
    - 偏好当前 `slot` 的员工在前
    - `roles.size` 更小的员工在前
    - `employeeId` 升序
  - 每条已分配记录至多生成 1 条建议，取排序后的第一名候选人
  - `reasons` 的生成顺序固定为：
    - 若该已分配记录来自冲突，加入 `conflict`
    - 若该已分配记录命中请假偏好，加入 `leave`
    - 若替换员工偏好当前 `slot`，加入 `preferred-slot`
  - `score = leavePriority + (冲突时加 3) + (替换员工偏好当前 slot 时加 1)`
  - suggestions 需要按 `(date, slot, role, fromEmployee, toEmployee)` 去重
  - suggestions 排序规则为：
    - `score` 降序
    - `date`、`slot`、`role`、`fromEmployee`、`toEmployee` 升序

- `renderPlan(result)` 必须返回 UTF-8 文本行列表，并严格使用下面的格式：
  - 第一段：
    - 第一行固定是 `SUMMARY`
    - 第二行固定是 `SUMMARY|<gapCount>|<conflictCount>|<suggestionCount>`
  - 第二段：
    - 标题行固定是 `GAPS`
    - 若没有 gap，输出单行 `GAP|-`
    - 否则每行格式为 `GAP|<date>|<slot>|<role>|<requiredStaff>|<employee1,employee2,...>|<missingCount>`
    - `assignedEmployees` 为空时输出 `-`
  - 第三段：
    - 标题行固定是 `CONFLICTS`
    - 若没有 conflict，输出单行 `CONFLICT|-`
    - 否则每行格式为 `CONFLICT|<employeeId>|<date>|<slot>|<role1,role2,...>`
  - 第四段：
    - 标题行固定是 `SUGGESTIONS`
    - 若没有 suggestion，输出单行 `SWAP|-`
    - 否则每行格式为 `SWAP|<date>|<slot>|<role>|<fromEmployee>|<toEmployee>|<score>|<reason1,reason2,...>`
    - `reasons` 为空时输出 `-`
  - 这四段之间必须各有一个空行

- `writePlan(result, outputPath)` 必须把 `renderPlan(result)` 生成的内容按原顺序写入文件，并以单个换行符结尾。

验证方式：

- 测试会直接编译 `/root/ShiftCoveragePlanner.scala`。
- 测试会按命令行方式运行 `ShiftCoveragePlanner`，检查生成的计划文件内容。
- 测试还会通过临时 harness 调用 `loadShiftNeeds`、`loadEmployeeSkills`、`loadLeavePreferences`、`planCoverage` 和 `renderPlan`，比较关键集合结果。
- 测试会同时使用题目给定的 CSV 与临时构造的新 CSV。
- 只要公开接口、排序规则和可观察结果一致，内部实现细节不限。
