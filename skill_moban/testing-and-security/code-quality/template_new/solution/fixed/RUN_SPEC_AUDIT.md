# Run Spec Audit

## Spec Summary

- `specs/export_contract.md`
- `specs/acceptance_criteria.md`
- `specs/quality_requirements.md`

这些文件共同定义了正式 gate 的 canonical evidence：

- `specs/export_contract.md` 定义 daily / monthly 的字段契约、净额公式、adjustment 事件范围和 batch fallback 语义。
- `specs/acceptance_criteria.md` 定义正式 gate 必须同时覆盖 `reference_batch` 和 `dirty_incident_batch`，并保持 `export -> validate -> summarize` 顺序。
- `specs/quality_requirements.md` 定义最小质量资产、功能测试覆盖面和可复核要求。

由此推出的 release invariants：

- `refund`、`chargeback`、`manual_adjustment`、`reserve_release` 都属于 adjustment 侧，不能静默丢弃。
- daily 必须保留 `processor_batch_id`，为空时回退到 `fallback_batch_id`。
- monthly 必须保留 `refund_count`、`chargeback_count`、`first_batch_id`、`last_batch_id`，且净额口径与 daily 一致。
- 正式通过标准不只是“生成文件”，而是“真实 gateway 接受四次正式验收”。

## Incident Replay

- `incidents/2026-04-12-missed-adjustments.md`
- `incidents/2026-04-16-batch-id-regression.md`

两次事故的第一处偏差分别是：

- `2026-04-12-missed-adjustments`：
  dirty data 进入导出后，`refund` / `chargeback` 被静默漏算，文件仍能生成，但 `adjustment_amount` 与 `net_settlement_amount` 已经偏离规格。
- `2026-04-16-batch-id-regression`：
  金额口径看起来仍然成立，但 `processor_batch_id` 为空且没有回退到 `fallback_batch_id`，导致 gateway 在真实验收阶段拒收。

这次回归验证必须证明：

- adjustment 漏算不会在 `reference_batch` 和 `dirty_incident_batch` 中重演。
- batch id 回退对 daily / monthly 都仍然有效。
- 事故风险已经被正式功能测试和真实 gateway 验收共同覆盖。

## Gateway Contract Diff

真实 gateway 暴露的契约点必须与仓库实现保持一致：

- route 必须仍然通过 `/api/v1/validate/daily` 和 `/api/v1/validate/monthly` 做正式验收。
- gateway 关注的核心字段包括 daily 的 `processor_batch_id`，以及 monthly 的 `refund_count`、`chargeback_count`、`first_batch_id`、`last_batch_id`。
- gateway 的接受 / 拒收结论必须来自实时调用，不能被离线 JSON 或历史快照替代。
- `export_summary.md` 需要把 gateway contract diff 的结果沉淀为可复核 evidence：至少包括 integrity 摘要和四次 validate 调用结果。

## Audit Questions

- Does the exporter preserve all adjustment event types required by the contract?
- Does the gateway-facing output keep batch id fallback semantics intact?
- Do monthly rows preserve the same net-settlement contract as daily rows?
- Does the formal gate still exercise dirty incident replay instead of only happy-path data?

## Audit Close-Out

- Any mismatch between code, incidents, and spec is release-blocking.
- A passing audit should map every major risk to either executable checks or documented review steps.
- A passing audit should leave behind a clear spec summary, an incident replay conclusion, and a gateway contract diff conclusion in this runbook.

## Optional Probe Commands

这些命令用于重跑审计，不替代上面的正式结论：

```bash
python3 /logs/agent/skills/settlement-quality-audit/scripts/probe_spec_summary.py --root / --limit 6
python3 /logs/agent/skills/settlement-quality-audit/scripts/probe_incident_replay.py --root / --limit-events 40
python3 /logs/agent/skills/settlement-quality-audit/scripts/probe_gateway_contracts.py --root / --gateway-root /services/settlement-gateway --show-matches
```
