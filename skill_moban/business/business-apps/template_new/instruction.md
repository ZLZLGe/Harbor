你需要为收入运营团队整理下一次续费与催收例会要用的行动台账。容器里已经放入较早导出的 CRM 和 invoice 快照，但它们可能缺项或状态滞后；本次交付应以 `ops_manifest.json` 指向的容器内 revops service 为准。

输入数据位于 `/root/data/`：

- `ops_manifest.json`：workspace 编号、cohort 日期、交付要求，以及本地 revops service 的 URL。
- `crm_export.csv`：较早导出的续费 cohort 与 CRM 字段快照，可能不完整。
- `invoice_snapshot.ndjson`：较早导出的 invoice 与 dunning 状态快照，可能不再代表当前状态。
- `action_policy.yaml`：本次续费工作台的动作分流规则与阈值。
- `contact_directory.csv`：客户负责人、区域和升级联系信息。

## 你的任务

1. 审查当前 cohort 中的全部账户，整理每个账户当前应进入的续费动作分流。
2. 结合 revops service 提供的当前账户事实，判断哪些账户需要发送 invoice、跟进回款、升级客户负责人、更新扩容报价或暂停续费。
3. 生成一份可直接给收入运营团队使用的结构化工作台账、一份汇总 JSON，以及一份简短业务摘要。

## 业务约束

1. cohort 中的每个账户都必须出现在最终台账里，不能遗漏。
2. `crm_export.csv` 和 `invoice_snapshot.ndjson` 只能作为背景参考，不能替代当前 revops service。
3. 续费动作必须依据当前 service 返回的事实和 `action_policy.yaml` 的规则决定。
4. 如果账户需要动作，必须给出唯一的 `action_bucket` 和唯一的 `action_reason`。
5. 不能通过删账户、删字段、删输出文件、停掉服务或改环境来规避约束。

## 输出

如 `/root/output/` 不存在，请先创建该目录。

1. 写入 `/root/output/renewal_worklist.csv`

列名必须严格如下：

```csv
account_id,company_name,crm_deal_id,owner_name,renewal_date,renewal_arr_usd,invoice_status,dunning_stage,seat_delta,action_bucket,action_reason,next_step
```

要求：

- 必须覆盖当前 cohort 中的全部账户，且每个 `account_id` 只能出现一次。
- `renewal_date` 使用 `YYYY-MM-DD`。
- `renewal_arr_usd` 必须写当前续费金额。
- `seat_delta` 必须写当前 preview 中的 seat 变化值。
- `action_bucket` 只能取以下值之一：
  - `send_invoice`
  - `collect_payment`
  - `escalate_csm`
  - `update_expansion_quote`
  - `pause_renewal`
  - `monitor`
- `action_reason` 只能取以下值之一：
  - `draft_invoice_ready`
  - `overdue_payment_attempts`
  - `missing_purchase_order`
  - `expansion_quote_required`
  - `legal_hold`
  - `healthy_autopay`
- `next_step` 必须是简短可执行说明。

2. 写入 `/root/output/renewal_control_summary.json`

顶层结构必须严格如下：

```json
{
  "workspace_id": "revops-000",
  "cohort_date": "YYYY-MM-DD",
  "totals": {
    "accounts_reviewed": 0,
    "renewal_arr_reviewed_usd": 0.0,
    "accounts_needing_action": 0,
    "revenue_at_risk_usd": 0.0
  },
  "action_counts": {
    "send_invoice": 0,
    "collect_payment": 0,
    "escalate_csm": 0,
    "update_expansion_quote": 0,
    "pause_renewal": 0,
    "monitor": 0
  },
  "workflow_blocked_account_ids": ["ACC-000"],
  "service_checks": {
    "revops_manifest": true,
    "accounts": true,
    "account_details": true,
    "renewal_previews": true,
    "dunning_events": true
  },
  "notes": [
    "Example note"
  ]
}
```

要求：

- `workspace_id` 和 `cohort_date` 必须与任务输入一致。
- `accounts_reviewed` 必须等于当前 cohort 的账户数。
- `renewal_arr_reviewed_usd` 必须等于全部账户当前 `renewal_arr_usd` 之和。
- `accounts_needing_action` 必须等于 `action_bucket != monitor` 的账户数。
- `revenue_at_risk_usd` 必须等于 `action_bucket != monitor` 的账户续费金额之和。
- `workflow_blocked_account_ids` 只记录当前因采购阻塞或法务限制而无法继续推进续费流程的账户，按 `account_id` 升序输出。
- `service_checks` 的 5 个字段都必须为 `true`。
- `notes` 至少包含 2 条业务摘要。

3. 写入 `/root/output/ops_brief.md`

内容必须包含：

- workspace 编号；
- cohort 日期；
- 当前账户总数；
- 需要动作的账户总数；
- 当前流程阻塞账户 ID；
- 当前最高金额的扩容报价账户；
- 当前最紧急的催收账户；
- 对本次动作分流逻辑的简短说明。

## 说明

- 不要修改 `/root/data/` 下的任何输入文件。
- 不要把较早导出的 CSV 或 NDJSON 当作唯一依据，也不要绕过当前容器内的 revops service。
- 不要用硬编码结果、缓存答案或手工拼接占位输出来代替当前链路。
- 不要修改 tests、verifier、task metadata、environment 文件或任何 `skills` 目录内容。
- 你可以在工作目录中编写辅助脚本，但最终只需要提交 `/root/output/` 下要求的 3 个文件。
