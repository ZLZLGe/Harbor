# Acceptance Criteria

正式质量 gate 必须同时满足下面三类要求：

## 1. Gateway Acceptance

- `reference_batch` 的 daily 和 monthly 都必须通过 gateway 验收。
- `dirty_incident_batch` 的 daily 和 monthly 都必须通过 gateway 验收。
- 验收必须通过本地 settlement gateway 完成，不能离线比对历史快照代替。

## 2. Quality Assets

仓库里必须存在并可复用以下质量资产：

- `quality/QUALITY.md`
- `quality/test_functional.py`
- `quality/RUN_CODE_REVIEW.md`
- `quality/RUN_INTEGRATION_TESTS.md`
- `quality/RUN_SPEC_AUDIT.md`
- `AGENTS.md`

这些资产不是装饰物。它们需要能帮助后续接手者理解：

- 关键业务风险是什么
- 每个 code review finding 需要哪些 supporting evidence
- 该先看 specs 还是 incidents
- dirty data 如何复现
- 怎样证明结果来自真实 gateway

## 3. Gate Semantics

- 顺序必须保持 `export -> validate -> summarize`
- 失败时需要非零退出
- 不允许把 dirty scenario 从正式 gate 中删掉
- `export_summary.md` 需要显式记录 `reference_batch` 和 `dirty_incident_batch` 的 daily / monthly 验收结果
- `export_summary.md` 需要留下可复核的 gateway evidence 摘要，而不是只写“passed”
