# 任务说明（缺陷回归 Harness 设计）

你需要读取缺陷工单 JSON，基于固定映射规则输出回归测试设计决策数组。

## 输入
- 输入文件：`/app/workspace/input/bug_tickets.json`
- 输入根结构：JSON 数组
- 每个工单对象包含以下字段：
  - `ticket_id`
  - `area`
  - `error_signal`
  - `has_workflow_json`
  - `has_stacktrace`
  - `has_sandbox_mode`
  - `has_production_mode`
  - `external_api`
  - `ui_surface`

## 输出
- 主输出文件：`/app/workspace/output/regression_harness.json`
- 输出根结构必须是 JSON 数组，不允许额外包裹对象。
- 数组中每个对象字段顺序固定为：
  - `ticket_id`
  - `test_layer`
  - `test_pattern`
  - `key_location`
  - `parity_check`
  - `artifact`
  - `fix_hint`

## 路由规则
根据 `area` 将工单映射到测试层与模式，保持与 `reproduce-bug` 技能表一致：

| area 信号 | test_layer | test_pattern | key_location |
| --- | --- | --- | --- |
| `node operation` | `unit` | `NodeTestHarness + nock` | `packages/nodes-base/nodes/*/test/` |
| `node credential` | `unit` | `jest-mock-extended` | `packages/nodes-base/nodes/*/test/` |
| `trigger webhook` | `unit` | `mock IHookFunctions + jest.mock GenericFunctions` | `packages/nodes-base/nodes/*/test/` |
| `binary data` | `unit` | `NodeTestHarness assertBinaryData` | `packages/core/nodes-testing/` |
| `execution engine` | `integration` | `WorkflowRunner + DI container` | `packages/cli/src/__tests__/` |
| `cli / api` 或 `api` | `API` | `setupTestServer + supertest` | `packages/cli/test/integration/` |
| `config` | `unit` | `GlobalConfig + Container` | `packages/@n8n/config/src/__tests__/` |
| `editor ui` | `UI` | `Vue Test Utils + Pinia` | `packages/frontend/editor-ui/src/**/__tests__/` |
| `e2e / canvas` 或 `canvas` | `E2E` | `Test containers + composables` | `packages/testing/playwright/` |

## 额外规则
1. 如果 `has_sandbox_mode = true` 且 `has_production_mode = true`，`parity_check` 必须为 `sandbox+production`。
2. 其他情况 `parity_check` 必须为 `single-path`。
3. `artifact` 必须是稳定的确定性字符串，不允许随机值。
4. `fix_hint` 必须是简洁、可执行的修复方向，不允许为空。
5. 输出数组必须按 `ticket_id` 升序排序。
6. 输出中不允许出现 `null`、`None`、`N/A`、空字符串等空值表达。
7. 除 JSON 结构本身外，不允许输出说明性文本。

## 禁止事项
- 不允许修改输入文件。
- 不允许访问网络或依赖外部服务。
- 不允许输出额外主结果文件替代 `regression_harness.json`。
