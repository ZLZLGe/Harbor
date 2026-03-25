你需要在一组审计准备工件中，为指定合规控制生成一条可追溯证据链。

输入位置：
- 请求说明：`/root/audit_request.json`
- 工件目录：`/root/audit_prep/`

你的目标：
1. 根据请求中的 `control_id`、`audit_cycle` 和 `audit_cutoff`，锁定该控制项在审计截止时点适用的最新版策略文档。
2. 输出与该控制项直接对应的补救 PR 列表。
3. 输出批准该最新版策略文档的审批员工 ID 列表。
4. 输出该控制项在当前审计周期仍然有效的例外说明 URL。
5. 为以上每一项结果提供可回溯的 `artifact_pointer`。

判定规则：
- “最新版策略文档”只看与目标控制项 `policy_family` 一致、`status` 为 `final`、且 `effective_date` 不晚于 `audit_cutoff` 的文档；不要把更新但仍是 draft 的版本、annex、或其他控制族的文档算进去。
- “补救 PR”只保留同时满足以下条件的条目：属于目标控制项、属于请求里的审计周期、状态为已合并、明确是 direct fix、并且关联到该控制项的 gap ticket。历史周期、evidence-only、仍未合并、或属于其他控制项的 PR 都不能输出。
- “审批员工 ID”只统计针对所选策略文档给出明确 `APPROVED` 动作的员工；提交人、评论人或其他文档的审批人都不能算进去。
- “例外说明 URL”只保留目标控制项在当前审计周期内仍有效、且状态为 approved 的例外记录；已过期、draft、或属于其他控制项/其他周期的例外不能输出。
- `artifact_pointer` 必须是相对 `/root` 的文件路径字符串，并带有 `#...` 片段定位到具体记录。
- 所有列表都必须去重并按字典序升序输出。

将结果写入 `/root/control_audit_trace.json`，JSON 结构必须如下：

```json
{
  "control_id": "CTRL-000",
  "policy_document": {
    "doc_id": "POL-XXX",
    "artifact_pointer": "audit_prep/...#..."
  },
  "remediation_prs": [
    {
      "pr_id": "PR-0000",
      "artifact_pointer": "audit_prep/...#..."
    }
  ],
  "approver_employee_ids": [
    {
      "employee_id": "eid_xxx",
      "artifact_pointer": "audit_prep/...#..."
    }
  ],
  "exception": {
    "url": "https://...",
    "artifact_pointer": "audit_prep/...#..."
  }
}
```

除了这个 JSON 文件，不需要额外输出其他答案文件。
