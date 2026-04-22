# Release Dry-Run Incident

本周的 staging release dry-run 不是完全失败，而是更糟的“表面完成、结果不可交付”：

- 产物目录有时会生成 bundle，但 on-call 检查时发现 promotion plan 与真实 broker 返回的不一致。
- 某些运行里 `release-summary.md` 仍然显示来自历史 snapshot，而不是当前 dry-run。
- 现在的多阶段流水线仍应保持 inspect -> package -> attest -> promote 的职责分离；值班要求是修复真实 release 链路，而不是把所有逻辑塞进一个一步到位的 shell。
- 历史 fallback 只用于排障比对，不是正式 release 数据源。

业务上，这条 dry-run 需要继续覆盖：

- live release candidates
- provenance / attestation 结果
- staging promotion plan

如果最终 bundle 把 metadata-only artifact 当作 deployable artifact，或 promotion plan 没有和当前 release candidates 对齐，这次事故仍然算未解决。
