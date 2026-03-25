#!/bin/bash

set -eu

PROJECT_ROOT="${TASK_PROJECT_ROOT:-/workspace/dispatch-board}"

mkdir -p "$PROJECT_ROOT/tests" "$PROJECT_ROOT/notes"

cat <<'EOF' > "$PROJECT_ROOT/tests/test_dispatch_contract.py"
import pytest

from dispatch_board import (
    DispatchBoardService,
    InMemoryDispatchClient,
    ServiceContractError,
)


@pytest.fixture
def client() -> InMemoryDispatchClient:
    return InMemoryDispatchClient(DispatchBoardService())


async def test_service_info_reports_inmemory_contract(client: InMemoryDispatchClient):
    payload = await client.get_service_info()

    assert payload["service"] == "dispatch-board"
    assert payload["transport"] == "inmemory"
    assert payload["tools"] == [
        "lookup_ticket",
        "list_escalations",
        "schedule_callback",
    ]


async def test_lookup_ticket_returns_expected_nested_snapshot(
    client: InMemoryDispatchClient,
):
    payload = await client.call_tool("lookup_ticket", {"ticket_id": "INC-42"})

    assert payload["tool"] == "lookup_ticket"
    assert payload["ticket"]["team"] == "routing"
    assert payload["ticket"]["severity"] == "high"
    assert payload["ticket"]["tags"] == ["vip", "after-hours"]
    assert payload["meta"]["source"] == "snapshot"


async def test_run_batch_keeps_result_order_and_batch_contract(
    client: InMemoryDispatchClient,
):
    payload = await client.run_batch(
        [
            {"tool": "list_escalations", "payload": {"team": "routing"}},
            {
                "tool": "schedule_callback",
                "payload": {
                    "ticket_id": "INC-42",
                    "owner": "mia",
                    "slot": "2026-03-25T09:30:00Z",
                },
            },
        ]
    )

    assert payload["transport"] == "inmemory"
    assert [item["tool"] for item in payload["results"]] == [
        "list_escalations",
        "schedule_callback",
    ]
    assert payload["results"][0]["items"][0]["ticket_id"] == "INC-42"
    assert payload["results"][1]["job"]["status"] == "queued"


async def test_close_ticket_raises_service_contract_error(
    client: InMemoryDispatchClient,
):
    with pytest.raises(ServiceContractError, match="unknown tool: close_ticket"):
        await client.call_tool("close_ticket", {"ticket_id": "INC-42"})
EOF

cat <<'EOF' > "$PROJECT_ROOT/notes/async_contract_report.md"
# Async Contract Report

所有场景都通过进程内客户端执行，本任务不依赖真实网络。

| interface | scenario | asserted_contract |
| --- | --- | --- |
| get_service_info | 读取服务元数据 | 返回 dispatch-board、inmemory，以及 3 个稳定工具名 |
| call_tool | 查询 INC-42 工单快照 | `team=routing`、`severity=high`、`tags=["vip", "after-hours"]`、`meta.source=snapshot` |
| run_batch | 批量执行升级列表与回呼排队 | 结果顺序保持 `list_escalations` 在前、`schedule_callback` 在后 |
| run_batch | 检查批量返回结构 | 第一条升级记录是 `INC-42`，回呼任务 `job.status=queued` |
| call_tool | 非法工具失败路径 | 调用 `close_ticket` 时抛出 `ServiceContractError`，消息为 `unknown tool: close_ticket` |
EOF
