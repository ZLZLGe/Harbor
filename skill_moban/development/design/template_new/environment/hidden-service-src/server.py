from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


WEATHER_IMPACT = {
    "source": "Port Aurelia Weather Operations API",
    "quarter": "FY2026 Q1",
    "events": [
        {
            "id": "WX-2026-02-COASTAL-RAIN",
            "label": "Feb 7-9 coastal rain band",
            "event_type": "heavy rain",
            "start_date": "2026-02-07",
            "end_date": "2026-02-09",
            "affected_zones": ["Waterfront", "North Campus"],
            "duration_hours": 42,
            "trip_change_pct": -18,
            "availability_change_pct": -14,
            "ops_note": "Battery swaps slowed and corral overflow increased near ferry stops."
        },
        {
            "id": "WX-2026-03-WIND",
            "label": "Mar 2 harbor wind advisory",
            "event_type": "wind advisory",
            "start_date": "2026-03-02",
            "end_date": "2026-03-03",
            "affected_zones": ["Waterfront"],
            "duration_hours": 19,
            "trip_change_pct": 7,
            "availability_change_pct": -21,
            "ops_note": "Ferry disruption pushed more riders to shared vehicles while rebalancing lagged."
        },
        {
            "id": "WX-2026-03-PARADE",
            "label": "Mar 11 parade detour",
            "event_type": "street closure",
            "start_date": "2026-03-11",
            "end_date": "2026-03-11",
            "affected_zones": ["Civic Core"],
            "duration_hours": 8,
            "trip_change_pct": -6,
            "availability_change_pct": -8,
            "ops_note": "Temporary station access issues created a short outage pocket."
        }
    ]
}

SERVICE_ZONES = {
    "city": "Port Aurelia",
    "zones": [
        {
            "zone": "Waterfront",
            "priority": "critical",
            "audience": "commuters and weekend visitors",
            "service_window": "05:30-23:30",
            "target_rebalance_minutes": 55
        },
        {
            "zone": "North Campus",
            "priority": "high",
            "audience": "students and staff",
            "service_window": "06:00-22:30",
            "target_rebalance_minutes": 50
        },
        {
            "zone": "Civic Core",
            "priority": "medium",
            "audience": "office and court district riders",
            "service_window": "06:00-21:00",
            "target_rebalance_minutes": 45
        },
        {
            "zone": "East Market",
            "priority": "medium",
            "audience": "retail workers and evening visitors",
            "service_window": "07:00-00:30",
            "target_rebalance_minutes": 48
        },
        {
            "zone": "Hilltop",
            "priority": "watch",
            "audience": "park and residential riders",
            "service_window": "07:00-20:00",
            "target_rebalance_minutes": 40
        }
    ]
}


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json({"ok": True})
        elif path == "/api/weather-impact":
            self._send_json(WEATHER_IMPACT)
        elif path == "/api/service-zones":
            self._send_json(SERVICE_ZONES)
        else:
            self._send_json({"error": "not found"}, 404)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8111), Handler).serve_forever()
