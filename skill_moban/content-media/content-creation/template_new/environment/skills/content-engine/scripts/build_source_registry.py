from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path


BASE_URL = os.environ.get("CONTENT_REVIEW_BASE_URL", "http://127.0.0.1:8147")
OUTPUT_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source_registry.json")


def fetch_json(path: str) -> dict:
    req = urllib.request.Request(
        BASE_URL.rstrip("/") + path,
        headers={"X-Client": "skill-build-source-registry"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    index = fetch_json("/api/index")
    constraints = fetch_json("/api/constraints")
    documents = []
    for doc in index["docs"]:
        documents.append(fetch_json(f"/api/document/{doc['doc_id']}"))

    payload = {
        "index": index,
        "constraints": constraints,
        "documents": documents,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(str(OUTPUT_PATH))


if __name__ == "__main__":
    main()
