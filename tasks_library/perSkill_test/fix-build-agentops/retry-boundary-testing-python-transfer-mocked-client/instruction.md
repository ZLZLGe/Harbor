# 任务说明

仓库已经放在 `/workspace/billing-relay`。

这里的 `InvoiceBillingGateway` 会封装第三方计费客户端，但目前缺少稳定的边界测试。请只补测试与审计摘要，在不访问真实服务的前提下验证它的重试语义。

请完成以下内容：

1. 重写 `tests/test_billing_gateway.py`
2. 生成 `reports/mock_retry_audit.txt`

`tests/test_billing_gateway.py` 必须满足：

- 使用 pytest。
- 使用 `unittest.mock` 在 `create_charge` 这个第三方边界上做 mock；不要访问真实网络，也不要引入 `requests`、`httpx`、`respx`、`vcrpy`、`subprocess` 或人为 `sleep`。
- 至少包含 4 个测试函数，其中至少 1 个使用 pytest fixture。
- 测试里要直接使用仓库里的 `InvoiceBillingGateway`、`ChargeResult`、`GatewayTimeoutError`、`GatewayDeclinedError`、`BillingDeclinedError`、`BillingUnavailableError`。
- 覆盖下面 4 个场景：
  - 当 `create_charge` 先连续抛出两次 `GatewayTimeoutError("temporary timeout")`，第三次返回 `{"charge_id": "ch_900", "status": "captured", "duplicate": false}` 时，调用 `InvoiceBillingGateway.capture_invoice(...)` 应成功返回 `ChargeResult`；并断言 mock 总调用次数是 3 次，3 次调用的 `idempotency_key` 全都等于 `idem-inv-100`。
  - 当 `create_charge` 抛出 `GatewayDeclinedError("card expired")` 时，断言抛出 `BillingDeclinedError`，错误消息包含 `card expired`，并且不重试，调用次数必须是 1。
  - 当 `create_charge` 连续 3 次抛出 `GatewayTimeoutError("temporary timeout")` 时，断言抛出 `BillingUnavailableError`，消息包含 `3 attempts`，并且调用次数正好是 3。
  - 对同一个 `invoice_id` / `idempotency_key` 连续调用两次 `capture_invoice(...)`，如果 mock 依次返回 `duplicate=False` 和 `duplicate=True` 且 `charge_id` 相同，断言第二次结果 `duplicate is True`，并且两次返回的 `remote_id` 相同。
- 保留文件名 `tests/test_billing_gateway.py`；不要通过删除、整体 skip、改名或改生产代码来绕过任务。

`reports/mock_retry_audit.txt` 必须满足：

- 第一行是 `Mock Retry Audit`
- 至少包含下面 6 行键值对，顺序不限：
  - `suite_status: complete`
  - `tested_entrypoint: InvoiceBillingGateway.capture_invoice`
  - `mock_boundary: create_charge`
  - `retry_success_attempts: 3`
  - `decline_mapping: BillingDeclinedError`
  - `idempotent_repeat_observed: true`
- 另外再包含一行简短说明，明确写到没有访问真实计费服务。

完成后，下面命令应能通过：

```bash
cd /workspace/billing-relay
pytest -q tests/test_billing_gateway.py
```
