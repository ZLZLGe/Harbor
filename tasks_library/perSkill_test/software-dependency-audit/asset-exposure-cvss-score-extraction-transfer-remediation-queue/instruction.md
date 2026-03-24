你在为下一轮补丁窗口准备修复排期。输入文件位于：

- `/root/asset_exposure.csv`
- `/root/vulnerability_records.json`

请生成 `/root/remediation_queue.tsv`，供运维按优先级安排修复。

输出 TSV 的列顺序必须严格为：
`Queue_Position	Asset_ID	Business_Service	Environment	Vulnerability_ID	Package	Installed_Version	Selected_CVSS	Score_Source	Exposure_Points	Priority_Score	Remediation_Band	Patch_Window	Fixed_Version	Reference_URL`

处理规则：

- 对每条漏洞记录，按 `nvd.v3_score` → `ghsa.v3_score` → `redhat.v3_score` 的优先级选择一个分数。
- `Score_Source` 只能写成 `NVD`、`GHSA`、`RedHat` 或 `N/A`。
- 如果三个来源都没有分数，则 `Selected_CVSS` 和 `Score_Source` 都写 `N/A`，`Priority_Score` 写 `0.0`。
- `Exposure_Points` 根据资产暴露表计算：
  - 基础分为 `criticality`
  - `internet_exposed` 为 `yes` 时额外加 `2`，否则加 `0`
  - `exposed_hosts >= 200` 再加 `3`
  - `50 <= exposed_hosts < 200` 再加 `2`
  - `exposed_hosts < 50` 再加 `1`
- `Priority_Score = Selected_CVSS * Exposure_Points`，保留 1 位小数；没有分数时固定写 `0.0`。
- `Remediation_Band` 规则：
  - `Priority_Score >= 60.0` 为 `P1`
  - `35.0 <= Priority_Score < 60.0` 为 `P2`
  - 其余为 `P3`
- `fixed_version` 为空字符串或缺失时写 `N/A`。
- `Selected_CVSS` 有分数时保留 1 位小数；没有分数时写 `N/A`。
- 输出队列按 `Priority_Score` 降序排序；如果相同，再按 `Asset_ID` 升序；如果仍相同，再按 `Vulnerability_ID` 升序。
- `Queue_Position` 从 `1` 开始，按最终输出顺序连续编号。

除了目标 TSV 外，不需要生成其他文件。
