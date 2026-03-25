# 背景

`/workspace/replay-sanitizer` 里有一个离线 Java 命令行工具，用来扫描历史回放样本目录，并生成可安全重放的清单。

输入样本位于 `/workspace/historical-corpus`。每个样本都是一个独立 JSON 文件，记录了 `sampleId`、抓取时间和一个待回放请求。当前实现直接把样本绑定成业务对象，再根据少数字段决定是否可重放。

这个流程有明显盲区：如果危险结构藏在业务对象不会保留的位置里，样本在对象化之后看起来可能“很正常”，但真实回放前的风险已经被遗漏。题目里的恶意样本会混合这几类问题：

- 任意深度的空字符串键 `""`
- 多态或类型注入指令键，例如 `@class`、`@type`、`@c`
- 带脚本执行倾向的嵌套对象，例如某个对象里出现 `type` 为 `javascript`、`groovy` 或 `spel`

# 你的任务

修复 `/workspace/replay-sanitizer`，然后基于提供的历史样本目录生成输出文件：

- 输入目录：`/workspace/historical-corpus`
- 输出文件：`/workspace/output/replay-remediation-manifest.json`

# 修复要求

1. 必须在生成安全清单之前，对每个原始 JSON 样本做递归结构检查，不能只依赖已经绑定好的业务对象。
2. 任何位置出现空字符串键 `""` 的样本都必须隔离，原因记为 `empty-key`。
3. 任何位置出现 `@class`、`@type` 或 `@c` 的样本都必须隔离，原因记为 `type-directive`。
4. 任何位置出现对象字段 `type` 的值为 `javascript`、`groovy` 或 `spel` 的样本都必须隔离，原因记为 `script-like-type`。
5. 无法解析的坏 JSON 也必须隔离，原因记为 `invalid-json`。
6. 合法样本仍然要保留在安全清单中，并输出规范化后的请求摘要；不要把整个批次一刀切失败。
7. 修复应聚焦在样本扫描与清洗逻辑本身，不需要额外大改项目结构。

# 输出契约

`/workspace/output/replay-remediation-manifest.json` 必须是一个 JSON 对象，至少包含这些字段：

- `batchId`
- `scannedSampleCount`
- `safeReplayCount`
- `quarantinedCount`
- `safeReplays`
- `quarantinedSamples`

其中：

- `safeReplays` 中每一项至少要包含 `sampleId`、`capturedAt`、`method`、`path`、`dataset`、`filterType`、`normalizedBody`
- `quarantinedSamples` 中每一项至少要包含 `sampleId`、`sourceFile`、`reasons`
- `safeReplays` 需要按 `sampleId` 升序输出，作为规范化结果的一部分
- `quarantinedSamples` 也需要按 `sampleId` 升序输出

# 验证重点

验证程序会检查这些可观察结果：

- 主输入目录会生成一份符合契约的清洗清单。
- 提供的历史样本里，合法样本仍然保留在 `safeReplays` 中。
- 含空字符串键、类型指令键、脚本型 `type` 值或坏 JSON 的样本会进入隔离列表。
- 对额外构造的 JSON 样本目录，工具仍然会按同样规则做递归隔离，而不是只对现成输入写死结果。
