# 任务说明（Cross Layer TDD Rollout）

你需要根据输入 CSV 中的特性信息，生成稳定、可程序化校验的跨层 TDD 推进计划 CSV。

## 输入
- 输入文件：`workspace/input/features.csv`
- 字段顺序固定为：
  - `feature_id`
  - `user_role`
  - `has_api`
  - `has_ui`
  - `has_external_service`
  - `risk_level`
- 其中 `has_api`、`has_ui`、`has_external_service` 只会使用 `yes` 或 `no`。
- `risk_level` 使用 `low`、`medium`、`high`、`critical` 之一。

## 输出
- 主输出文件：`/app/workspace/output/tdd_rollout.csv`
- 输出字段必须且仅能按以下顺序出现：
  - `feature_id`
  - `user_journey`
  - `unit_focus`
  - `integration_focus`
  - `e2e_focus`
  - `coverage_gate`
  - `checkpoint_plan`

## 处理规则
1. 每条输入记录必须生成一条输出记录，不允许丢行。
2. 输出必须按 `feature_id` 升序排序。
3. `user_journey` 必须以用户旅程为先，且明确“先写测试再写代码”：
   - `has_ui=yes` 且 `has_api=yes`：`<user_role> journey -> UI to API before code`
   - `has_ui=yes` 且 `has_api=no`：`<user_role> journey -> UI interaction before code`
   - `has_ui=no` 且 `has_api=yes`：`<user_role> journey -> API flow before code`
   - `has_ui=no` 且 `has_api=no`：`<user_role> journey -> offline workflow before code`
4. `unit_focus` 必须体现单元测试优先和错误路径覆盖：
   - `has_ui=yes` 且 `has_api=yes`：`domain rules;UI state;API adapters;error paths`
   - `has_ui=yes` 且 `has_api=no`：`domain rules;UI state;error paths`
   - `has_ui=no` 且 `has_api=yes`：`domain rules;API handlers;error paths`
   - `has_ui=no` 且 `has_api=no`：`domain rules;pure functions;error paths`
5. `integration_focus` 规则：
   - `has_external_service=yes` 且 `has_api=yes`：`API contracts;persistence;external failure path`
   - `has_external_service=yes` 且 `has_api=no`：`module seams;external failure path`
   - `has_external_service=no` 且 `has_api=yes`：`API contracts;persistence`
   - `has_external_service=no` 且 `has_api=no`：`module seams only`
6. `e2e_focus` 规则：
   - `has_ui=yes` 且 `has_external_service=yes`：`happy path;dependency outage`
   - `has_ui=yes` 且 `has_external_service=no` 且 `has_api=yes`：`happy path;API validation failure`
   - `has_ui=yes` 且 `has_external_service=no` 且 `has_api=no`：`happy path;client validation failure`
   - `has_ui=no` 且 `has_api=yes`：`consumer smoke;auth failure`
   - `has_ui=no` 且 `has_api=no` 且 `has_external_service=yes`：`orchestrator smoke;dependency outage`
   - `has_ui=no` 且 `has_api=no` 且 `has_external_service=no`：`batch smoke;invalid input`
7. `coverage_gate` 由 `risk_level` 决定：
   - `critical` -> `unit>=95%;integration>=90%;e2e=required`
   - `high` -> `unit>=90%;integration>=80%;e2e=required`
   - `medium` -> `unit>=85%;integration>=70%;e2e=targeted`
   - `low` -> `unit>=80%;integration>=60%;e2e=smoke`
8. `checkpoint_plan` 必须固定输出为：`journey-tests -> unit-red-green -> integration-red-green -> e2e-error-path -> coverage-gate`
9. 若某字段无法计算，写空字符串；禁止输出 `null`、`None`、`nan`、`N/A` 等空值替代字符串。

## 禁止事项
- 不允许修改输入文件。
- 不允许改变输出字段名、字段顺序或主输出路径。
- 不允许引入联网、随机数或主观判断。
- 不允许输出额外主结果文件替代 `tdd_rollout.csv`。
