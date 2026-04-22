from __future__ import annotations

import os
from datetime import datetime, timezone

import requests
from rollout_api.summary_projection import project_summary_items


class IncidentFeedUnavailableError(RuntimeError):
    pass


class IncidentFeedClient:
    def __init__(self) -> None:
        self.base_url = os.environ.get("INCIDENT_FEED_BASE_URL", "")
        self.client_id = os.environ.get("MANAGED_IDENTITY_CLIENT_ID", "")
        self.scope = os.environ.get("MIRROR_RESOURCE_SCOPE", "") or os.environ.get("MIRROR_SCOPE", "")

    def _headers(self) -> dict[str, str]:
        return {
            "X-Managed-Identity-Client": self.client_id,
            "X-Mirror-Scope": self.scope,
        }

    def fetch_live(self, *, region: str, service: str) -> dict:
        if not self.base_url:
            raise IncidentFeedUnavailableError("INCIDENT_FEED_BASE_URL is not configured")

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/incidents",
                params={"region": region, "service": service},
                headers=self._headers(),
                timeout=5,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise IncidentFeedUnavailableError(f"mirror request failed: {exc}") from exc
        except ValueError as exc:
            raise IncidentFeedUnavailableError("mirror response was not valid JSON") from exc

        if "snapshot_id" not in payload or "items" not in payload:
            raise IncidentFeedUnavailableError("mirror response did not include snapshot_id and items")

        return payload

    def fetch_public_payload(self, *, region: str, service: str) -> dict:
        return self.fetch_live(region=region, service=service)


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _sort_items(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda item: (
            _parse_timestamp(item.get("opened_at")),
            _parse_timestamp(item.get("updated_at")),
            item.get("tracking_id", ""),
        ),
        reverse=True,
    )


def _latest_incident_id(items: list[dict]) -> str | None:
    if not items:
        return None
    return _sort_items(items)[0].get("tracking_id")


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
    latest_id = _latest_incident_id(summary_items)
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
