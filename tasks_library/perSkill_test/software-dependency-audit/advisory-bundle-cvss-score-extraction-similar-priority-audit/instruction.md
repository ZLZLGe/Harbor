你接手的是一份已经离线导出的依赖告警包，输入文件位于 `/root/advisory_bundle.json`。

请从其中筛出所有严重级别为 `HIGH` 或 `CRITICAL` 的依赖漏洞，并写出审计结果到 `/root/advisory_priority_audit.csv`。

输出 CSV 的列顺序必须严格为：
`Artifact,Package,Installed_Version,Advisory_ID,Severity,CVSS_Score,Score_Source,Fixed_Version,Title,Reference_URL`

处理规则：

- 只保留 `HIGH` 和 `CRITICAL`。
- 每条告警的 `cvss` 可能同时包含多个来源的 `v3_score`。
- 选分规则固定为：先取 `nvd.v3_score`，否则取 `ghsa.v3_score`，否则取 `redhat.v3_score`，如果都没有则写 `N/A`。
- `Score_Source` 分别写成 `NVD`、`GHSA`、`RedHat` 或 `N/A`。
- `fixed_version` 为空或缺失时写 `N/A`。
- 保留原始的 `artifact`、`title` 和参考链接。

除了目标 CSV 外，不需要生成其他说明文件。
