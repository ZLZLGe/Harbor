from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PORT = int(os.environ.get("CONTENT_REVIEW_PORT", "8147"))
SOURCE_ROOT = Path(os.environ.get("SOURCE_BUNDLE_ROOT", "/root/workspace/source_bundle"))
ACCESS_LOG = Path(os.environ.get("CONTENT_REVIEW_ACCESS_LOG", "/var/log/content-review/access.log"))


@dataclass(frozen=True)
class Document:
    doc_id: str
    path: str
    kind: str
    title: str
    source_url: str
    topics: list[str]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_documents() -> tuple[dict, dict[str, Document]]:
    index = read_json(SOURCE_ROOT / "source_index.json")
    docs: dict[str, Document] = {}
    for raw in index["docs"]:
        docs[raw["doc_id"]] = Document(
            doc_id=raw["doc_id"],
            path=raw["path"],
            kind=raw["kind"],
            title=raw["title"],
            source_url=raw["source_url"],
            topics=list(raw.get("topics", [])),
        )
    return index, docs


INDEX, DOCS = load_documents()
CONSTRAINTS = read_json(SOURCE_ROOT / "campaign_constraints.json")
RED_FLAGS = [
    line.strip()
    for line in (SOURCE_ROOT / "style_red_flags.txt").read_text(encoding="utf-8").splitlines()
    if line.strip()
]


def build_document_payload(doc: Document) -> dict:
    file_path = SOURCE_ROOT / doc.path
    lines = file_path.read_text(encoding="utf-8").splitlines()
    return {
        "doc_id": doc.doc_id,
        "path": doc.path,
        "kind": doc.kind,
        "title": doc.title,
        "source_url": doc.source_url,
        "topics": doc.topics,
        "line_count": len(lines),
        "lines": [{"line": idx, "text": text} for idx, text in enumerate(lines, start=1)],
    }


def log_request(path: str, query: dict[str, list[str]], client: str, status: int) -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": path,
        "query": query,
        "client": client,
        "status": status,
    }
    with ACCESS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "content-review/1.0"

    def log_message(self, format: str, *args) -> None:
        return

    def _json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        client = self.headers.get("X-Client", "unknown")
        query = parse_qs(parsed.query)

        if parsed.path == "/health":
            self._json({"ok": True, "service": "content-review"})
            log_request(parsed.path, query, client, HTTPStatus.OK)
            return

        if parsed.path == "/api/index":
            self._json(
                {
                    "campaign_id": INDEX["campaign_id"],
                    "theme": INDEX["theme"],
                    "docs": INDEX["docs"],
                }
            )
            log_request(parsed.path, query, client, HTTPStatus.OK)
            return

        if parsed.path == "/api/constraints":
            self._json(
                {
                    "campaign_constraints": CONSTRAINTS,
                    "style_red_flags": RED_FLAGS,
                }
            )
            log_request(parsed.path, query, client, HTTPStatus.OK)
            return

        prefix = "/api/document/"
        if parsed.path.startswith(prefix):
            doc_id = parsed.path[len(prefix) :]
            doc = DOCS.get(doc_id)
            if doc is None:
                self._json({"error": "document_not_found", "doc_id": doc_id}, status=404)
                log_request(parsed.path, query, client, HTTPStatus.NOT_FOUND)
                return
            self._json(build_document_payload(doc))
            log_request(parsed.path, query, client, HTTPStatus.OK)
            return

        self._json({"error": "not_found", "path": parsed.path}, status=404)
        log_request(parsed.path, query, client, HTTPStatus.NOT_FOUND)


def main() -> None:
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
