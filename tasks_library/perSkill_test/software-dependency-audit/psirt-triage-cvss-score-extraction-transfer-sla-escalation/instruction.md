你在做厂商 PSIRT 公告分诊。输入文件位于：

- `/root/vendor_psirt_feed.json`
- `/root/remediation_tickets.json`

请把超过修复 SLA 的高风险事项整理成 `/root/psirt_sla_escalations.json`。

本题的评审基准时间固定为 `2026-03-20`，不要使用系统当前日期。

处理规则：

- 每条公告包含多个 `vulnerabilities`。
- 对每个 vulnerability，按 `nvd.v3_score` → `ghsa.v3_score` → `redhat.v3_score` 的优先级选择一个分数。
- `score_source` 分别写成 `NVD`、`GHSA`、`RedHat`；如果都没有分数则写 `N/A`。
- 每条公告的 `best_cvss_score` 取该公告下所有 vulnerability 的已选分数中的最大值。
- `best_vulnerability_id` 和 `score_source` 需要对应到这个最大分数所在的 vulnerability。
- 如果整条公告都没有可用分数，则把 `best_cvss_score`、`best_vulnerability_id` 和 `score_source` 都写成 `N/A`。
- 只有同时满足以下条件的公告才进入升级清单：
  - `best_cvss_score` 至少为 `7.0`
  - 公告对应工单的 `status` 不是 `resolved` 或 `deployed`
  - `sla_due_date` 早于 `2026-03-20`
- `days_overdue` 按 `2026-03-20 - sla_due_date` 的整天差值计算。
- 输出中的 `escalations` 必须按 `days_overdue` 降序排序；如果相同，再按 `advisory_id` 升序排序。

输出 JSON 结构必须为：

```json
{
  "generated_for_date": "2026-03-20",
  "minimum_cvss_for_escalation": 7.0,
  "escalations": [
    {
      "advisory_id": "string",
      "ticket_id": "string",
      "product": "string",
      "owner": "string",
      "status": "string",
      "best_vulnerability_id": "string or N/A",
      "best_cvss_score": 0.0,
      "score_source": "NVD/GHSA/RedHat/N/A",
      "sla_due_date": "YYYY-MM-DD",
      "days_overdue": 0,
      "published_at": "YYYY-MM-DD",
      "bulletin_url": "string"
    }
  ]
}
```

除了目标 JSON，不需要生成其他文件。
