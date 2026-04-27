#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


INPUT_DIR = Path("/root/brandroom/input")
LOG_PATH = Path("/var/log/brandroom/access.log")


def read_sources() -> list[dict]:
    rows = []
    with (INPUT_DIR / "source_corpus.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_claims() -> list[dict]:
    with (INPUT_DIR / "allowed_claims.csv").open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def read_json(name: str) -> dict:
    return json.loads((INPUT_DIR / name).read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    server_version = "BrandroomArchive/1.0"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def write_log(self, status: int, body_bytes: int) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": time.time(),
            "client": self.headers.get("X-Client", ""),
            "method": self.command,
            "path": urlparse(self.path).path,
            "status": status,
            "bytes": body_bytes,
        }
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    def send_json(self, payload: object, status: int = 200) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        self.write_log(status, len(data))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/health":
                self.send_json({"ok": True, "service": "brandroom-archive"})
            elif path == "/api/sources":
                self.send_json({"sources": read_sources()})
            elif path == "/api/claims":
                self.send_json({"claims": read_claims()})
            elif path == "/api/brief":
                self.send_json(read_json("campaign_brief.json"))
            elif path == "/api/channel-specs":
                self.send_json(read_json("channel_specs.json"))
            elif path == "/api/glossary":
                self.send_json(read_json("glossary.json"))
            else:
                self.send_json({"error": "not found"}, status=404)
        except Exception as exc:
            self.send_json({"error": type(exc).__name__, "message": str(exc)}, status=500)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8137), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
