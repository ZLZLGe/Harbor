# 任务说明（React 渠道测试路由与特性开关计划）

你需要读取 React 测试请求 CSV，生成规范化的测试执行计划 CSV。

## 输入
- 输入文件：`/app/workspace/input/react_test_requests.csv`
- 输入字段必须存在且顺序如下：
  - `case_id`
  - `channel`
  - `variant`
  - `pattern`
  - `needs_gate`
  - `flag_name`
  - `scenario`

## 输出
- 主输出文件：`/app/workspace/output/react_test_plan.csv`
- 输出字段必须存在且顺序固定：
  - `case_id`
  - `command`
  - `gate_strategy`
  - `flag_check`
  - `expected_channel_state`
  - `notes`

## 处理规则
1. 必须逐行读取输入，并为每个 `case_id` 生成一行输出。
2. `channel` 规范化规则：
   - `source` 或空白值都视为 `source`
   - `experimental` 视为实验渠道
   - `www` 结合 `variant` 生成 www-modern 指令
   - `stable` 视为稳定渠道
   - `classic` 视为 www-classic 渠道
3. `command` 必须严格按以下映射生成：
   - `source` -> `yarn test --silent --no-watchman <pattern>`
   - `experimental` -> `yarn test -r=experimental --silent --no-watchman <pattern>`
   - `stable` -> `yarn test-stable --silent --no-watchman <pattern>`
   - `classic` -> `yarn test-classic --silent --no-watchman <pattern>`
   - `www` 且 `variant` 不是 `false` -> `yarn test-www --silent --no-watchman <pattern>`
   - `www` 且 `variant` 为 `false` -> `yarn test-www --variant=false --silent --no-watchman <pattern>`
4. `variant` 仅对 `www` 有效；当 `channel` 不是 `www` 时，忽略 `variant`。
5. `gate_strategy` 规则：
   - 若 `needs_gate` 规范化后为 `yes`，且 `scenario` 为 `unavailable_without_flag`，输出 `@gate <flag_name>`
   - 若 `needs_gate` 规范化后为 `yes`，且 `scenario` 为 `behavior_differs_by_flag`，输出 `gate()`
   - 其他情况输出 `none`
6. `flag_check` 规则：
   - 若 `gate_strategy == none`，输出 `not-needed`
   - `source` 且需要检查特性开关时，输出 `<flag_name>=source-default`
   - `experimental` 且需要检查特性开关时，输出 `<flag_name>=experimental-on`
   - `stable` 且需要检查特性开关时，输出 `<flag_name>=stable-default`
   - `classic` 且需要检查特性开关时，输出 `<flag_name>=classic-default`
   - `www` 且 `variant` 不是 `false` 时，输出 `<flag_name>=variant:true`
   - `www` 且 `variant` 为 `false` 时，输出 `<flag_name>=variant:false`
7. `expected_channel_state` 规则：
   - `source` -> `source-default`
   - `experimental` -> `experimental-enabled`
   - `stable` -> `stable-release`
   - `classic` -> `www-classic`
   - `www` 且 `variant` 不是 `false` -> `www-modern-variant-true`
   - `www` 且 `variant` 为 `false` -> `www-modern-variant-false`
8. `notes` 规则：
   - `gate_strategy == none` -> `baseline route`
   - `gate_strategy` 以 `@gate ` 开头 -> `skip unless flag enabled`
   - `gate_strategy == gate()` -> `assert both flag branches`
9. 输出必须按 `case_id` 升序排序。
10. 输出中不得出现额外列，也不得改变字段顺序。

## 精度、空值与禁止事项
- 所有字段都必须输出为精确字符串，不允许额外空格。
- 不允许输出 `null`、`None`、`nan`、`NaN`、空字符串。
- 不允许修改输入文件。
- 不允许联网、随机化、依赖系统时间或外部服务。
- 不允许生成除 `/app/workspace/output/react_test_plan.csv` 之外的结果文件来替代主输出。
