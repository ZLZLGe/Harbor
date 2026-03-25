你需要在一组客户升级响应工件中，为指定账户生成一份承诺履约简报。

输入位置：
- 请求说明：`/root/escalation_request.json`
- 工件目录：`/root/customer_ops/`

你的目标：
1. 根据请求中的 `account_id`、`escalation_id` 和 `cutoff`，锁定本次客户升级当前仍有效的客户承诺。
2. 输出本次升级当前受影响的 `customer_id` 列表。
3. 对每个有效承诺，输出承诺摘要、负责 `owner_employee_id`、直接对应的修复 PR、作出该承诺的会议记录、以及最近一次对客户共享的演示链接。
4. 为每个承诺标注截止时点之前最新的状态证据。

判定规则：
- 只保留同时满足以下条件的承诺：属于请求里的 `account_id` 和 `escalation_id`，在承诺台账中 `customer_committed = true`，并且 `status = "active"`。历史升级、相似账户、`internal_only`、已关闭或被替代的承诺都不能输出。
- `affected_customer_ids` 只取目标升级简报里的当前影响范围；不要混入历史升级或其他账户的客户。
- `fix_prs` 只保留同一承诺、同一账户、同一升级、`status = "merged"` 且 `change_type = "direct_fix"` 的 PR。`prep_only`、`follow_up`、未合并、或属于其他账户/升级的 PR 不能输出。
- `meeting_record` 必须指向该承诺首次被标记为 `commit_to_customer` 的会议记录。
- `demo_link` 必须选择同一承诺在截止时点前最近一次对客户共享的演示链接；只接受 `status = "shared"` 且 `audience = "customer"` 的记录。
- `latest_status` 必须选择截止时点前、同一承诺最新的一条客户可见状态消息；只接受 `visibility = "customer"` 且 `kind` 为 `customer_commitment` 或 `status_update` 的消息。
- `artifact_pointer` 必须是相对 `/root` 的路径字符串，并带 `#...` 片段定位到具体记录。
- 所有列表都必须去重并按字典序稳定排序：`affected_customer_ids` 按 customer ID 升序，`commitments` 按 `commitment_id` 升序，`fix_prs` 按 `pr_id` 升序。

将结果写入 `/root/customer_escalation_brief.json`，JSON 结构必须如下：

```json
{
  "account_id": "ACC-000",
  "escalation_id": "ESC-000",
  "affected_customer_ids": ["CUST-001"],
  "commitments": [
    {
      "commitment_id": "COM-001",
      "summary": "承诺摘要",
      "owner_employee_id": "eid_xxx",
      "fix_prs": [
        {
          "pr_id": "PR-001",
          "artifact_pointer": "customer_ops/...#..."
        }
      ],
      "meeting_record": {
        "meeting_id": "MTG-001",
        "artifact_pointer": "customer_ops/...#..."
      },
      "demo_link": {
        "url": "https://...",
        "artifact_pointer": "customer_ops/...#..."
      },
      "latest_status": {
        "state": "delivered",
        "summary": "最新状态摘要",
        "artifact_pointer": "customer_ops/...#..."
      }
    }
  ]
}
```

除了这个 JSON 文件，不需要额外输出其他答案文件。
