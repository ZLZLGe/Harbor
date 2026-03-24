你在准备候选发布版本的门禁评审。输入文件位于：

- `/root/release_candidate_snapshot.json`
- `/root/release_gate_policy.json`

请生成 `/root/release_gate_brief.md`，用于说明本次候选发布是否触发阻断发布的风险阈值。

处理规则：

- 对每条 advisory，按 `nvd.v3_score` → `ghsa.v3_score` → `redhat.v3_score` 的优先级选择一个分数。
- `Score_Source` 只能写成 `NVD`、`GHSA`、`RedHat` 或 `N/A`。
- 如果三个来源都没有分数，则 `Selected_CVSS` 和 `Score_Source` 都写 `N/A`。
- `fixed_version` 为空字符串或缺失时写 `N/A`。
- `High-Risk Advisories` 指已选分数大于等于 `high_risk_score_floor` 的 advisory 数量。
- 只要满足以下任一条件，就判定 `Decision: BLOCK`，否则为 `Decision: PASS`：
  - 至少一条 advisory 的已选分数大于等于 `block_if_any_score_at_least`
  - `High-Risk Advisories` 数量大于等于 `block_if_high_risk_count_at_least`
- advisory 表格按以下顺序排序：
  - 先按已选分数从高到低排序
  - 没有分数的行放在最后
  - 分数相同时按 `advisory_id` 升序

输出 Markdown 必须严格使用下面的结构、标题和字段名：

```md
# Release Gate Brief

- Release ID: <release_id>
- Service: <service>
- Planned Release Date: <planned_release_date>
- Policy: <policy_name> (<policy_version>)

## Gate Decision
- Decision: PASS or BLOCK
- Blocking Threshold Triggered: YES or NO
- Trigger Reason: <一句完整英文说明>

## Risk Summary
- Advisories Reviewed: <整数>
- Advisories With Selected Scores: <整数>
- High-Risk Advisories (>= <high_risk_score_floor>): <整数>
- Unscored Advisories: <整数>

## Selected Advisory Scores
| Component | Artifact | Advisory_ID | Package | Selected_CVSS | Score_Source | Fixed_Version | Reference_URL |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ... |
```

补充要求：

- `Selected_CVSS` 有分数时保留一位小数；没有分数时写 `N/A`。
- `Trigger Reason` 必须同时说明“是否有 advisory 达到单项阻断分数阈值”和“达到高风险分数下限的 advisory 数量是否达到阻断数量阈值”。
- 除目标 Markdown 外，不需要生成其他文件。
