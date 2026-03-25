# 任务说明

仓库已经放在 `/workspace/dispatch-board`。

这里有一个异步工具服务，但现有的 `tests/test_dispatch_contract.py` 仍然依赖本地端口，属于脆弱的网络测试。请把它改造成稳定的进程内契约测试，并补一份覆盖说明。

请完成以下内容：

1. 重写 `tests/test_dispatch_contract.py`
2. 生成 `notes/async_contract_report.md`

`tests/test_dispatch_contract.py` 必须满足：

- 使用 pytest，且至少包含 4 个 `async def` 测试函数。
- 至少包含 1 个 pytest fixture，并基于仓库内现成的 `DispatchBoardService` 与 `InMemoryDispatchClient` 组织测试。
- 保留文件名 `tests/test_dispatch_contract.py`，不要通过删除、整体 skip 或改名来绕过。
- 所有场景都只能在进程内完成；不要使用真实网络、`localhost` / `127.0.0.1` URL、`RemoteDispatchClient`、`requests`、`httpx`、`subprocess` 或人为 `sleep`。
- 覆盖下面这些异步接口契约：
  - `await client.get_service_info()`：断言返回的 `service` 是 `dispatch-board`，`transport` 是 `inmemory`，`tools` 精确等于 `["lookup_ticket", "list_escalations", "schedule_callback"]`
  - `await client.call_tool("lookup_ticket", {"ticket_id": "INC-42"})`：断言返回里 `ticket.team == "routing"`、`ticket.severity == "high"`、`ticket.tags == ["vip", "after-hours"]`，并且 `meta.source == "snapshot"`
  - `await client.run_batch(...)`：至少同时覆盖 `list_escalations` 与 `schedule_callback` 两种调用，断言批量结果顺序保持不变；其中 `list_escalations` 的第一条记录必须是 `INC-42`，`schedule_callback` 的 `job.status` 必须是 `queued`
  - 至少 1 个失败场景：对 `close_ticket` 发起调用时，断言抛出 `ServiceContractError`，并匹配消息 `unknown tool: close_ticket`

`notes/async_contract_report.md` 必须满足：

- 第一行是 `# Async Contract Report`
- 明确写到本任务不依赖真实网络
- 包含一个 Markdown 表格，表头必须是 `| interface | scenario | asserted_contract |`
- 表格至少 4 行数据，概括你覆盖的接口与断言

完成后，下面命令应能通过：

```bash
cd /workspace/dispatch-board
pytest -q tests/test_dispatch_contract.py
```
