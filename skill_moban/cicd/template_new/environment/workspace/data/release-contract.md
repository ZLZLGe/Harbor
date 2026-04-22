# Release Contract

release dry-run 的正式输出需要满足以下契约：

1. `release-bundle.json`
   - `source` 必须反映 bundle 当前使用的数据来源。
   - `artifacts` 需要保留 live broker 提供的 artifact 元数据。
   - `summary.deployable_count` 只统计真正可进入 promotion plan 的 artifact。
   - `summary.attested_count` 只统计 deployable artifact 中 provenance 验证成功的数量。
   - `summary.promotion_ready_count` 只统计可进入 staging promotion 的 artifact 数量。

2. `promotion-plan.json`
   - 必须来自当前 release 对应的 live broker plan。
   - 只包含当前 release 中真正 deployable 且 attested 的 artifact。

3. `release-summary.md`
   - 需要明确记录 release id、bundle source、promotion source 和 plan id。

注意：
- `stable` channel 不等于一定可 deploy；例如 metadata-only artifact 可以属于 stable release，但不能进入 staging promotion。
- 历史 fallback 仅供人工对比，不应成为正式输出来源。
