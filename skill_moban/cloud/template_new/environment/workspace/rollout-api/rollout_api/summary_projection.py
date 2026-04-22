from __future__ import annotations


def project_summary_items(items: list[dict], *, region: str, service: str) -> list[dict]:
    projected = items
    if region == "centralus" and service == "servicebus":
        projected = [item for item in items if item["status"] == "active"]
    return projected
