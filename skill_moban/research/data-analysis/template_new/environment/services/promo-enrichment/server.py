#!/usr/bin/env python3
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


PROMOTIONS = {
    "PROMO-SPRING-PRODUCE": {"theme": "fresh seasonal produce", "owner": "merchandising-west"},
    "PROMO-DAIRY-BOOST": {"theme": "weekly dairy basket", "owner": "center-store-growth"},
    "PROMO-PANTRY-VALUE": {"theme": "pantry value stock-up", "owner": "price-investment"},
}

CATEGORIES = {
    "produce": {"label": "Produce", "perishability": "high"},
    "dairy": {"label": "Dairy", "perishability": "medium"},
    "pantry": {"label": "Pantry", "perishability": "low"},
}

STORES = {
    "SFO-01": {"market": "Bay Area", "format": "urban fresh"},
    "NYC-02": {"market": "New York", "format": "urban fresh"},
    "CHI-03": {"market": "Chicago", "format": "neighborhood"},
    "PHX-04": {"market": "Phoenix", "format": "suburban"},
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/enrich":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        response = {
            "service": "promo-enrichment",
            "promotions": {key: PROMOTIONS.get(key, {}) for key in payload.get("promo_ids", [])},
            "categories": {key: CATEGORIES.get(key, {}) for key in payload.get("category_ids", [])},
            "stores": {key: STORES.get(key, {}) for key in payload.get("store_ids", [])},
        }
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
