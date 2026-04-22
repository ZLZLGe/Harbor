#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


PORT = int(os.environ.get("DOMAIN_SNAPSHOT_PORT", "8331"))
DATA_ROOT = Path(
    os.environ.get("DOMAIN_SNAPSHOT_DATA_ROOT", "/services/domain-audit/snapshots")
)
CANDIDATES_PATH = Path(
    os.environ.get("DOMAIN_SNAPSHOT_CANDIDATES_PATH", "/app/data/candidate_domains.csv")
)


def _load_candidates() -> list[str]:
    rows = CANDIDATES_PATH.read_text(encoding="utf-8").strip().splitlines()[1:]
    return [row.split(",")[0] for row in rows]


def _load_snapshot(domain: str) -> dict[str, Any]:
    path = DATA_ROOT / f"{domain}.json"
    if not path.exists():
        raise FileNotFoundError(domain)
    return json.loads(path.read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json({"ok": True, "service": "domain-local-snapshots"})
            return
        if self.path == "/manifest":
            self._send_json(
                {
                    "segment": "field-service-dispatch-intelligence",
                    "service": "domain-local-snapshots",
                    "snapshot_endpoint_template": "/snapshots/<domain>",
                    "candidates": _load_candidates(),
                }
            )
            return
        if self.path.startswith("/snapshots/"):
            domain = self.path.rsplit("/", 1)[-1]
            try:
                self._send_json(_load_snapshot(domain))
            except FileNotFoundError:
                self._send_json({"error": "snapshot not found", "domain": domain}, status=404)
            return
        self._send_json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
