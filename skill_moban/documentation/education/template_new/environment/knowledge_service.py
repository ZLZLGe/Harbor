#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path("/workspace/session_bundle")


def read_json(relative_path):
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


MANIFEST = read_json("incident_manifest.json")
TICKET = read_json("tickets/TCK-1842.json")
LMS = read_json("metadata/lms_snapshot.json")
CONTRACT = read_json("metadata/course_contract.json")
INVENTORY = read_json("repository_inventory.json")
REVIEW_TEXT = (ROOT / "reviews/reviewer_notes.md").read_text(encoding="utf-8")
CI_TEXT = (ROOT / "logs/publish_ci.log").read_text(encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/health":
            self._send(200, {
                "ok": True,
                "snapshot_id": MANIFEST["snapshot_id"],
                "incident_count": 1,
                "course_count": 1
            })
            return

        if path == "/incidents/TCK-1842":
            self._send(200, {
                "manifest": MANIFEST,
                "ticket": TICKET,
                "ci_warnings": [
                    line for line in CI_TEXT.splitlines() if "warning" in line.lower()
                ],
                "review_recommendation": "Capture a reusable skill for linked course publishing contract checks."
            })
            return

        if path == "/courses/BIO-201/contract":
            self._send(200, {
                "lms_snapshot": LMS,
                "course_contract": CONTRACT,
                "detected_drifts": [
                    "module order violates prerequisite contract",
                    "caption/transcript parity job skipped",
                    "quiz rubric does not match current learning objective"
                ]
            })
            return

        if path == "/review-findings" and query.get("incident") == ["TCK-1842"]:
            self._send(200, {
                "incident_id": "TCK-1842",
                "findings": [
                    "Treat course metadata, learner-facing assets, accessibility artifacts, reviewer comments, and assessment rubrics as a linked publishing contract.",
                    "A reusable skill is more appropriate than a short instruction because the prevention path is multi-step, evidence-driven, and likely to recur across courses.",
                    "Future checks should cover caption/transcript mismatch, quiz rubric drift from learning objectives, and LMS metadata ordering drift."
                ],
                "source_excerpt": REVIEW_TEXT[:900]
            })
            return

        if path == "/repository/inventory":
            self._send(200, INVENTORY)
            return

        self._send(404, {"error": "not found", "path": self.path})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
