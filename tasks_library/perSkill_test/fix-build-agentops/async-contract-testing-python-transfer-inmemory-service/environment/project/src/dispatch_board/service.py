from __future__ import annotations

import asyncio
from urllib.parse import urlparse


class ServiceContractError(RuntimeError):
    """Raised when a caller asks for an unsupported tool contract."""


TICKET_SNAPSHOTS = {
    "INC-42": {
        "ticket_id": "INC-42",
        "team": "routing",
        "severity": "high",
        "owner": "mia",
        "status": "open",
        "tags": ["vip", "after-hours"],
    },
    "INC-77": {
        "ticket_id": "INC-77",
        "team": "routing",
        "severity": "medium",
        "owner": "noah",
        "status": "triage",
        "tags": ["billing"],
    },
}

ESCALATION_QUEUE = [
    {"ticket_id": "INC-42", "queue": "priority", "wait_minutes": 18},
    {"ticket_id": "INC-77", "queue": "standard", "wait_minutes": 7},
]


class DispatchBoardService:
    async def get_service_info(self) -> dict[str, object]:
        await asyncio.sleep(0)
        return {
            "service": "dispatch-board",
            "transport": "inmemory",
            "version": "2026.03",
            "tools": [
                "lookup_ticket",
                "list_escalations",
                "schedule_callback",
            ],
        }

    async def call_tool(
        self,
        tool_name: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        await asyncio.sleep(0)
        data = payload or {}

        if tool_name == "lookup_ticket":
            ticket_id = str(data.get("ticket_id", ""))
            if ticket_id not in TICKET_SNAPSHOTS:
                raise ServiceContractError(f"unknown ticket: {ticket_id}")
            return {
                "tool": "lookup_ticket",
                "ticket": dict(TICKET_SNAPSHOTS[ticket_id]),
                "meta": {
                    "source": "snapshot",
                    "refreshed_at": "2026-03-24T08:30:00Z",
                },
            }

        if tool_name == "list_escalations":
            team = str(data.get("team", "routing"))
            items = [
                dict(item)
                for item in ESCALATION_QUEUE
                if TICKET_SNAPSHOTS[item["ticket_id"]]["team"] == team
            ]
            return {
                "tool": "list_escalations",
                "team": team,
                "count": len(items),
                "items": items,
            }

        if tool_name == "schedule_callback":
            ticket_id = str(data.get("ticket_id", ""))
            if ticket_id not in TICKET_SNAPSHOTS:
                raise ServiceContractError(f"unknown ticket: {ticket_id}")
            owner = str(data.get("owner", ""))
            slot = str(data.get("slot", ""))
            return {
                "tool": "schedule_callback",
                "accepted": True,
                "job": {
                    "ticket_id": ticket_id,
                    "owner": owner,
                    "slot": slot,
                    "channel": "phone",
                    "status": "queued",
                },
            }

        raise ServiceContractError(f"unknown tool: {tool_name}")


class InMemoryDispatchClient:
    def __init__(self, service: DispatchBoardService | None = None) -> None:
        self._service = service or DispatchBoardService()

    async def get_service_info(self) -> dict[str, object]:
        return await self._service.get_service_info()

    async def call_tool(
        self,
        tool_name: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return await self._service.call_tool(tool_name, payload)

    async def run_batch(
        self,
        calls: list[dict[str, object]],
    ) -> dict[str, object]:
        results = []
        for call in calls:
            results.append(
                await self.call_tool(
                    str(call["tool"]),
                    dict(call.get("payload", {})),
                )
            )
        return {
            "transport": "inmemory",
            "results": results,
        }


class RemoteDispatchClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    async def _open_socket(self) -> None:
        parsed = urlparse(self._base_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 9511
        reader, writer = await asyncio.open_connection(host, port)
        writer.close()
        await writer.wait_closed()
        del reader
        raise ConnectionError(
            f"dispatch server at {self._base_url} did not speak the expected protocol"
        )

    async def get_service_info(self) -> dict[str, object]:
        await self._open_socket()
        raise AssertionError("unreachable")

    async def call_tool(
        self,
        tool_name: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        del tool_name, payload
        await self._open_socket()
        raise AssertionError("unreachable")

    async def run_batch(
        self,
        calls: list[dict[str, object]],
    ) -> dict[str, object]:
        del calls
        await self._open_socket()
        raise AssertionError("unreachable")
