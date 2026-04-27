#!/usr/bin/env python3
import hashlib
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


def build_context(candidates):
    canonical = []
    fields = {}
    for item in sorted(candidates, key=lambda row: row["candidate_id"]):
        field_id = item["field_id"]
        fields.setdefault(field_id, {"n_candidates": 0, "filters": set(), "candidate_ids": []})
        fields[field_id]["n_candidates"] += 1
        fields[field_id]["filters"].add(item.get("filter", "unknown"))
        fields[field_id]["candidate_ids"].append(item["candidate_id"])
        canonical.append(
            f"{item['candidate_id']}|{field_id}|{float(item['ra_icrs_deg']):.7f}|{float(item['dec_icrs_deg']):.7f}"
        )

    field_summary = {}
    for field_id, value in fields.items():
        field_summary[field_id] = {
            "n_candidates": value["n_candidates"],
            "filters": sorted(value["filters"]),
            "candidate_ids": sorted(value["candidate_ids"]),
            "density_class": "sparse" if value["n_candidates"] <= 2 else "review_cluster",
        }

    return {
        "service": "field-context",
        "service_version": "2026.04",
        "n_candidates": len(candidates),
        "request_checksum": hashlib.sha256("\n".join(canonical).encode("utf-8")).hexdigest(),
        "fields": field_summary,
    }


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/context":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        response = build_context(payload.get("candidates", []))
        body = json.dumps(response, sort_keys=True).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
