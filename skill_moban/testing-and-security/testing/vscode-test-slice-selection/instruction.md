# 任务说明（VS Code 测试切片选择）

你需要读取测试请求 CSV，生成 VS Code 测试执行选择 CSV。

## 输入
- 输入文件：`/app/workspace/input/test_requests.csv`
- 输入字段顺序固定如下：
  - `request_id`
  - `test_kind`
  - `file_filter`
  - `glob_filter`
  - `grep_filter`
  - `suite_filter`
  - `coverage`
  - `platform`

## 输出
- 主输出文件：`/app/workspace/output/vscode_test_selection.csv`
- 输出字段必须存在且顺序固定如下：
  - `request_id`
  - `script`
  - `arguments`
  - `scope`
  - `compile_required`
  - `notes`

## 处理规则
1. `request_id` 必须原样保留，并且输出结果必须按 `request_id` 升序排序。
2. `test_kind == unit` 时：
   - 必须选择单元测试脚本：
     - `platform == windows` 时输出 `.\scripts\test.bat`
     - 其他平台输出 `./scripts/test.sh`
   - 单元测试优先遵循 `runTests` / `scripts/test.sh` 语义：
     - 若 `file_filter` 非空，使用源文件路径作为位置参数，不要改写为集成测试脚本。
     - 若 `glob_filter` 非空且 `file_filter` 为空，使用 `--runGlob "<glob_filter>"`。
     - 若 `grep_filter` 非空，追加 `--grep "<grep_filter>"`。
     - 若 `coverage == true`，追加 `--coverage`。
   - `suite_filter` 对单元测试无效，不写入 `arguments`，但必须在 `notes` 中明确说明已忽略。
3. `test_kind == integration` 时：
   - 必须选择集成测试脚本：
     - `platform == windows` 时输出 `.\scripts\test-integration.bat`
     - 其他平台输出 `./scripts/test-integration.sh`
   - `coverage` 仅适用于单元测试；集成测试侧不得写入 `--coverage`，并且必须在 `notes` 中说明已忽略。
   - 若 `suite_filter` 非空，说明目标是 extension host suites：
     - `arguments` 必须包含 `--suite "<suite_filter>"`
     - 若 `grep_filter` 非空，可追加 `--grep "<grep_filter>"`
     - 此时忽略 `file_filter` 与 `glob_filter`，并在 `notes` 中说明。
   - 若 `suite_filter` 为空且 `file_filter` 非空，使用 `--run <file_filter>`；这会把范围缩小到 node 集成测试。
   - 若 `suite_filter` 为空且 `file_filter` 为空但 `glob_filter` 非空，使用 `--runGlob "<glob_filter>"`；这也会把范围缩小到 node 集成测试。
   - 若仅有 `grep_filter`，使用 `--grep "<grep_filter>"`；此时表示同时作用于 node 集成测试和 extension host suites。
4. `scope` 必须根据最终选择写成以下之一：
   - `unit`
   - `integration-node`
   - `integration-extension`
   - `integration-all`
5. `compile_required` 必须输出小写字符串 `true`，因为这些 VS Code 测试都依赖已编译产物。
6. `arguments` 必须是可直接执行的 shell 参数字符串，只能包含根据规则选择出来的参数，不得出现 `null`、`None`、`nan`、`NaN` 等空值样式文本。
7. `notes` 必须给出简洁、明确、确定性的说明；不得为空，也不得输出任何空值样式文本。

## 禁止事项
- 不允许修改输入文件。
- 不允许联网、随机化或依赖外部服务。
- 不允许输出额外列，或改变输出字段顺序。
- 不允许把单元测试请求路由到 `test-integration` 脚本。
- 不允许把集成测试请求路由到 `test.sh` / `test.bat`。
- 不允许在集成测试输出中保留 `--coverage`。
