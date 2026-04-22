#!/usr/bin/env python3

import csv
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DATA_PATH = Path(
    os.environ.get(
        "PANEL_ANNOTATION_DATA",
        "/services/panel-annotation/annotations.tsv",
    )
)
HOST = os.environ.get("PANEL_ANNOTATION_HOST", "127.0.0.1")
PORT = int(os.environ.get("PANEL_ANNOTATION_PORT", "9103"))


def load_annotations() -> dict[str, dict[str, str]]:
    with DATA_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return {row["gene_id"]: row for row in reader}


ANNOTATIONS = load_annotations()


class AnnotationHandler(BaseHTTPRequestHandler):
    def _write_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/annotate":
            self._write_json({"error": "not_found"}, status=404)
            return

        query = parse_qs(parsed.query)
        genes_arg = query.get("genes", [""])[0]
        gene_ids = [gene_id for gene_id in genes_arg.split(",") if gene_id]

        annotations = [ANNOTATIONS[gene_id] for gene_id in gene_ids if gene_id in ANNOTATIONS]
        missing = [gene_id for gene_id in gene_ids if gene_id not in ANNOTATIONS]

        self._write_json(
            {
                "annotations": annotations,
                "missing_genes": missing,
                "requested_gene_count": len(gene_ids),
            }
        )

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), AnnotationHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
