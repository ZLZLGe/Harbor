from __future__ import annotations


def project_summary_items(items: list[dict], *, region: str, service: str) -> list[dict]:
    del region, service
    return [item for item in items if item.get("summary_eligible", True)]
