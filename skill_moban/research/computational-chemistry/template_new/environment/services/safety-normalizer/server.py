#!/usr/bin/env python3
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DATA = Path("/root/workspace/data/safety_reports.jsonl")


def load_reports() -> list[dict]:
    reports: list[dict] = []
    if DATA.exists():
        for line in DATA.read_text(encoding="utf-8").splitlines():
            if line.strip():
                reports.append(json.loads(line))
    return reports


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/safety":
            self.send_response(404)
            self.end_headers()
            return
        query = parse_qs(parsed.query)
        name = query.get("compound_name", [""])[0].lower()
        rows = [
            row for row in load_reports()
            if row.get("compound_name", "").lower() == name
            or row.get("matched_name", "").lower() == name
        ]
        body = json.dumps({"reports": rows}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
