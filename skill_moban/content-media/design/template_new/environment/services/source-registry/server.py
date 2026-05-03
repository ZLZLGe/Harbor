#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DATA_PATH = Path(
    os.environ.get(
        "SOURCE_CATALOG_PATH",
        "/root/environment/data/sources/source_catalog.json",
    )
)
LOG_PATH = Path(
    os.environ.get("SOURCE_REGISTRY_LOG_PATH", "/tmp/source-registry-requests.log")
)
HOST = os.environ.get("SOURCE_REGISTRY_HOST", "127.0.0.1")
PORT = int(os.environ.get("SOURCE_REGISTRY_PORT", "4873"))


def load_catalog() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    server_version = "source-registry/1.0"

    def log_message(self, format: str, *args) -> None:
        return

    def _write_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _record(self) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{self.path}\n")

    def do_GET(self) -> None:
        self._record()
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        catalog = load_catalog()
        sources = {item["source_id"]: item for item in catalog["sources"]}

        if path == "/health":
            self._write_json(
                HTTPStatus.OK,
                {"ok": True, "service": "source-registry", "count": len(sources)},
            )
            return

        if path == "/sources":
            self._write_json(HTTPStatus.OK, catalog)
            return

        if path.startswith("/sources/"):
            source_id = path.split("/", 2)[2]
            if source_id not in sources:
                self._write_json(
                    HTTPStatus.NOT_FOUND,
                    {"ok": False, "error": f"unknown source id: {source_id}"},
                )
                return
            self._write_json(HTTPStatus.OK, sources[source_id])
            return

        self._write_json(
            HTTPStatus.NOT_FOUND,
            {"ok": False, "error": f"unknown path: {path}"},
        )


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"source registry listening on http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
