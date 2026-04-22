from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from rollout_api.summary_projection import project_summary_items


FALLBACK_PATH = Path(os.environ.get("ROLLOUT_FALLBACK_PATH", "/app/workspace/data/fallback_incidents.json"))


class IncidentFeedClient:
    def __init__(self) -> None:
        self.base_url = os.environ.get("INCIDENT_FEED_BASE_URL", "")
        self.client_id = os.environ.get("MANAGED_IDENTITY_CLIENT_ID", "")
        self.scope = os.environ.get("MIRROR_RESOURCE_SCOPE", "")

    def _headers(self) -> dict[str, str]:
        return {
            "X-Managed-Identity-Client": self.client_id,
            "X-Mirror-Scope": self.scope,
        }

    def fetch_live(self, *, region: str, service: str) -> dict:
        if not self.base_url:
            raise RuntimeError("INCIDENT_FEED_BASE_URL is not configured")

        response = requests.get(
            f"{self.base_url}/api/v1/incidents",
            params={"region": region, "service": service},
            headers=self._headers(),
            timeout=5,
        )
        response.raise_for_status()
        return response.json()

    def fetch_public_payload(self, *, region: str, service: str) -> dict:
        try:
            return self.fetch_live(region=region, service=service)
        except Exception:  # noqa: BLE001
            fallback = json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))
            items = [
                item
                for item in fallback["items"]
                if item["region"] == region and item["service_slug"] == service
            ]
            return {
                "snapshot_id": fallback["snapshot_id"],
                "items": items,
            }


def _sort_items(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: item["opened_at"])


def health_check() -> tuple[bool, str]:
    client = IncidentFeedClient()
    try:
        client.fetch_live(region="eastus2", service="containerapps")
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    return True, "ok"


def build_summary(*, region: str, service: str) -> dict:
    client = IncidentFeedClient()
    payload = client.fetch_public_payload(region=region, service=service)
    items = _sort_items(payload["items"])
    summary_items = project_summary_items(items, region=region, service=service)
    latest_id = summary_items[0]["tracking_id"] if summary_items else None
    open_items = [item for item in summary_items if item["status"] == "active"]
    critical_open = [item for item in open_items if item["severity"] == "critical"]

    return {
        "region": region,
        "service": service,
        "snapshot_id": payload["snapshot_id"],
        "incident_count": len(summary_items),
        "open_incident_count": len(open_items),
        "critical_open_count": len(critical_open),
        "latest_incident_id": latest_id,
    }


def build_incident_list(*, region: str, service: str) -> dict:
    client = IncidentFeedClient()
    payload = client.fetch_public_payload(region=region, service=service)
    items = _sort_items(payload["items"])
    return {
        "snapshot_id": payload["snapshot_id"],
        "items": items,
    }
