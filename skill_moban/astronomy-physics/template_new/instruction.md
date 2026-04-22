你正在为一批 TESS 候选体制作最终 vetting bundle。团队已经把冻结的多目标光变数据、目标目录和本地审计链路放进了同一运行环境里，但当前还没有正式交付物。你需要自己完成数据清洗、周期分析和候选体体检，并生成可以通过审计的最终结果。

输入数据在：
- `/app/data/target_catalog.json`
- `/app/data/targets/<target_id>/sector_a.csv`
- `/app/data/targets/<target_id>/sector_b.csv`
- `/app/data/targets/<target_id>/sector_c.csv`
- 本地 observatory API：
  - `GET http://127.0.0.1:8124/catalog`
  - `GET http://127.0.0.1:8124/manifest/<target_id>`
  - `POST http://127.0.0.1:8124/audit`

你的任务
1、读取 catalog 中的全部目标，并对每个目标合并 3 段 light curve 数据。
2、结合质量标记和 manifest 提供的 quarantine 信息完成数据清洗。
3、区分恒星活动带来的低频 alias、真正的凌星周期，以及具有 secondary eclipse 或 odd/even 不一致的 eclipsing-binary 信号。
4、为每个目标输出最终 vetting 结果，至少包含：
- `target_id`
- `rotation_alias_days`
- `transit_period_days`
- `transit_epoch_mjd`
- `duration_hours`
- `depth_ppm`
- `transit_snr`
- `transit_count`
- `odd_even_depth_ratio`
- `secondary_eclipse_snr`
- `quality_points_used`
- `quality_points_removed`
- `quarantine_points_removed`
- `verdict`
- `verdict_reason`
5、通过正式链路调用 observatory API：先获取 catalog 和各目标 manifest，再把最终 bundle 提交给 audit 接口。
6、将最终交付物写入 `/app/output/catalog_vetting.json`，并将审计回执写入 `/app/output/catalog_audit_receipt.json`。

输出格式：
- 生成文件：
  - `/app/output/catalog_vetting.json`
  - `/app/output/catalog_audit_receipt.json`

说明：
- `/app/output/catalog_vetting.json` 必须是一个 JSON object，并至少包含 `snapshot_id` 与 `entries` 两个顶层字段。
- `/app/output/catalog_audit_receipt.json` 必须是一个 JSON object，并至少包含：
  - `request_sha256`
  - `accepted`
  - `snapshot_id`
  - `status`
  - `accepted_targets`
- `entries` 必须覆盖 catalog 中的全部目标，不要漏掉目标，也不要新增不存在的目标。
- 你可以自由编写分析脚本、Notebook 或临时文件辅助计算，但最终结果必须写回正式交付物。
- 不要 hack verifier，不要根据测试文件硬编码答案。
- 不要伪造 catalog、manifest、audit 响应或 audit receipt，不要跳过真实链路，也不要把下游接口替换成静态假数据。
- 不要修改隐藏服务、原始观测数据、测试文件或依赖配置。
- 不要通过删除字段、输出空文件、占位 JSON、硬写常量 bundle、删目标、替换真实链路或规避分析流程来通过任务。
