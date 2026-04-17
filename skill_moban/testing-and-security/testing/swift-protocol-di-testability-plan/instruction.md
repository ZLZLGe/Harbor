# 任务说明（Swift Protocol DI Testability Plan）

你需要读取组件测试需求输入 CSV，生成稳定、可程序化校验的 Swift 可测试性改造计划 CSV。

## 输入
- 输入文件：`workspace/input/swift_components.csv`
- 字段顺序固定为：
  - `component_id`
  - `has_filesystem`
  - `has_network`
  - `has_external_api`
  - `needs_preview_support`
  - `needs_error_path`
- 所有布尔字段取值均为 `yes` 或 `no`。

## 输出
- 主输出文件：`/app/workspace/output/swift_di_testability_plan.csv`
- 输出字段必须且仅能按以下顺序出现：
  - `component_id`
  - `protocol_split`
  - `default_impls`
  - `mock_plan`
  - `injection_style`
  - `test_focus`
  - `concurrency_note`

## 处理规则
1. 每条输入记录生成一条输出记录，不允许丢行。
2. 必须体现基于协议的依赖注入思路：将外部关注点拆分为小而专注的协议，不要合并成单个大协议。
3. `protocol_split`：
   - 按固定顺序检查 `has_filesystem`、`has_network`、`has_external_api`。
   - 为值为 `yes` 的项分别加入：
     - `FileSystemProviding`
     - `NetworkTransporting`
     - `ExternalAPIProviding`
   - 若三项均为 `no`，输出 `Keep concrete core; extract protocols only for real external seams`。
   - 多项之间用 `;` 连接。
4. `default_impls`：
   - 对应上面的协议，按同样顺序输出默认生产实现名称：
     - `DefaultFileSystemProvider`
     - `DefaultNetworkTransport`
     - `DefaultExternalAPIClient`
   - 若没有外部依赖，输出 `No live adapter needed`。
   - 多项之间用 `;` 连接。
5. `mock_plan`：
   - 对应上面的协议，按同样顺序输出测试替身名称：
     - `MockFileSystemProvider`
     - `MockNetworkTransport`
     - `MockExternalAPIClient`
   - 若没有外部依赖，基础值为 `Use direct value-based tests`。
   - 若 `needs_error_path=yes`，在基础值后追加 `with configurable error cases`；若基础值里已有内容则使用 `;` 连接。
6. `injection_style`：
   - 基础值为 `Initializer injection with default live adapters`。
   - 若 `needs_preview_support=yes`，输出 `Initializer injection with default live adapters; override in tests and SwiftUI previews`。
7. `test_focus`：
   - 若存在任一外部依赖，首段输出 `Use Swift Testing to cover success paths per protocol seam`。
   - 否则首段输出 `Use Swift Testing on pure logic without extra protocol mocks`。
   - 若 `needs_error_path=yes`，追加 `exercise thrown failures via mock error toggles`。
   - 若 `needs_preview_support=yes`，追加 `verify preview wiring with injected stubs`。
   - 多段之间用 `;` 连接。
8. `concurrency_note`：
   - 若 `has_network=yes` 或 `has_external_api=yes`，输出 `Protocols and mocks should be Sendable; keep async collaborators actor-safe`。
   - 否则若 `has_filesystem=yes`，输出 `Make filesystem seams Sendable when crossing actor boundaries`。
   - 否则输出 `Only add Sendable if the type crosses concurrency boundaries`。
9. 排序规则：按 `component_id` 升序排序。
10. 空值规则：禁止输出 `null`、`None`、`nan` 等空值字符串；若规则已给出固定文案，必须使用该固定文案。

## 禁止事项
- 不允许修改输入文件。
- 不允许改变输出字段名、字段顺序或主输出路径。
- 不允许引入联网、随机数或主观判断。
- 不允许输出额外主结果文件替代 `swift_di_testability_plan.csv`。
