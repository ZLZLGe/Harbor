#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

DATA_PATH = Path("/root/research_packet/evidence_snapshot.json")


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def paper_to_bibtex(paper):
    fields = {
        "title": paper["title"],
        "author": " and ".join(paper["authors"]),
        "year": str(paper["year"]),
        "url": paper.get("url", "")
    }
    if paper.get("doi"):
        fields["doi"] = paper["doi"]
    if paper.get("arxiv"):
        fields["eprint"] = paper["arxiv"]
        fields["archivePrefix"] = "arXiv"
    if "Proceedings" in paper["venue"] or paper["source_type"] == "conference":
        entry_type = "inproceedings"
        fields["booktitle"] = paper["venue"]
    else:
        entry_type = "article"
        fields["journal"] = paper["venue"]
    body = ",\n".join(f"  {key} = {{{value}}}" for key, value in fields.items() if value)
    return f"@{entry_type}{{{paper['canonical_key']},\n{body}\n}}\n"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_text(self, payload, status=200):
        encoded = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        data = load_data()
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        papers = data["papers"]

        if path == "/":
            self._send_json({
                "service": data["service_name"],
                "snapshot_id": data["snapshot_id"],
                "endpoints": ["/health", "/papers", "/papers/{id}", "/search?q=...", "/bibtex/{id}", "/unverified", "/duplicates"]
            })
            return
        if path == "/health":
            self._send_json({"ok": True, "snapshot_id": data["snapshot_id"], "paper_count": len(papers)})
            return
        if path == "/papers":
            self._send_json({"papers": papers})
            return
        if path == "/unverified":
            self._send_json({"unverified_records": data["unverified_records"]})
            return
        if path == "/duplicates":
            self._send_json({"duplicates": data["duplicates"]})
            return
        if path.startswith("/papers/"):
            paper_id = unquote(path.split("/", 2)[2])
            for paper in papers:
                if paper_id in {paper["id"], paper["canonical_key"]}:
                    self._send_json(paper)
                    return
            self._send_json({"error": "paper not found"}, status=404)
            return
        if path.startswith("/bibtex/"):
            paper_id = unquote(path.split("/", 2)[2])
            for paper in papers:
                if paper_id in {paper["id"], paper["canonical_key"]}:
                    self._send_text(paper_to_bibtex(paper))
                    return
            self._send_text("paper not found\n", status=404)
            return
        if path == "/search":
            query = parse_qs(parsed.query).get("q", [""])[0].lower()
            terms = [term for term in query.replace("-", " ").split() if len(term) > 2]
            results = []
            for paper in papers:
                haystack = " ".join([
                    paper["title"],
                    paper["abstract"],
                    " ".join(paper["findings"]),
                    " ".join(paper["methods"])
                ]).lower()
                score = sum(1 for term in terms if term in haystack)
                if score:
                    item = dict(paper)
                    item["score"] = score
                    results.append(item)
            results.sort(key=lambda item: (-item["score"], item["year"], item["title"]))
            self._send_json({"query": query, "results": results})
            return
        self._send_json({"error": "unknown endpoint"}, status=404)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    server.serve_forever()
