#!/usr/bin/env python3

import json
import random
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FIXTURE_SEED = 271828
SHARD_SPECS = [
    {"pages": 7, "delay_bias": 142, "delay_step": 7, "size_bias": 2, "tenant": "beacon"},
    {"pages": 3, "delay_bias": 58, "delay_step": 4, "size_bias": 0, "tenant": "lagoon"},
    {"pages": 4, "delay_bias": 66, "delay_step": 5, "size_bias": 1, "tenant": "delta"},
    {"pages": 2, "delay_bias": 47, "delay_step": 3, "size_bias": 0, "tenant": "atlas"},
    {"pages": 6, "delay_bias": 151, "delay_step": 6, "size_bias": 2, "tenant": "beacon"},
    {"pages": 3, "delay_bias": 61, "delay_step": 4, "size_bias": 1, "tenant": "harbor"},
    {"pages": 4, "delay_bias": 71, "delay_step": 5, "size_bias": 1, "tenant": "delta"},
    {"pages": 2, "delay_bias": 52, "delay_step": 3, "size_bias": 0, "tenant": "atlas"},
    {"pages": 7, "delay_bias": 146, "delay_step": 7, "size_bias": 3, "tenant": "harbor"},
    {"pages": 3, "delay_bias": 63, "delay_step": 4, "size_bias": 1, "tenant": "lagoon"},
    {"pages": 3, "delay_bias": 69, "delay_step": 4, "size_bias": 0, "tenant": "delta"},
    {"pages": 2, "delay_bias": 49, "delay_step": 3, "size_bias": 0, "tenant": "atlas"},
    {"pages": 6, "delay_bias": 155, "delay_step": 6, "size_bias": 2, "tenant": "beacon"},
    {"pages": 3, "delay_bias": 59, "delay_step": 4, "size_bias": 1, "tenant": "harbor"},
    {"pages": 4, "delay_bias": 73, "delay_step": 5, "size_bias": 1, "tenant": "lagoon"},
    {"pages": 2, "delay_bias": 48, "delay_step": 3, "size_bias": 0, "tenant": "atlas"},
]
EVENT_TYPES = ["upsert", "snapshot", "compaction", "heartbeat", "repair", "rebalance"]


def build_fixture():
    shards = []
    all_records = []
    next_record_id = 1000

    for shard_index, spec in enumerate(SHARD_SPECS):
        rng = random.Random(FIXTURE_SEED + shard_index * 97)
        shard_id = f"shard-{shard_index:02d}"
        pages = []

        for page_number in range(spec["pages"]):
            page_size = 2 + spec["size_bias"] + rng.randint(0, 3)
            delay_ms = spec["delay_bias"] + rng.randint(0, 26) + page_number * spec["delay_step"]
            if page_number == spec["pages"] - 1 and spec["pages"] >= 6:
                delay_ms += 24

            records = []
            for offset in range(page_size):
                record = {
                    "record_id": next_record_id,
                    "tenant": spec["tenant"],
                    "shard_id": shard_id,
                    "page_number": page_number,
                    "offset_in_page": offset,
                    "event_type": EVENT_TYPES[(shard_index + page_number + offset) % len(EVENT_TYPES)],
                    "payload": f"{spec['tenant']}-{shard_id}-{page_number}-{offset}",
                }
                records.append(record)
                all_records.append(record)
                next_record_id += 1

            pages.append(
                {
                    "page_number": page_number,
                    "delay_ms": delay_ms,
                    "records": records,
                }
            )

        shards.append({"shard_id": shard_id, "tenant": spec["tenant"], "pages": pages})

    return {
        "seed": FIXTURE_SEED,
        "shards": shards,
        "all_records": all_records,
        "total_pages": sum(len(shard["pages"]) for shard in shards),
    }


FIXTURE = build_fixture()
SHARD_LOOKUP = {shard["shard_id"]: shard for shard in FIXTURE["shards"]}


class MockShardRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        segments = [segment for segment in path.strip("/").split("/") if segment]

        if segments == ["v1", "shards"]:
            payload = {
                "seed": FIXTURE["seed"],
                "shards": [{"shard_id": shard["shard_id"]} for shard in FIXTURE["shards"]],
            }
            return self._write_json(payload)

        if len(segments) == 5 and segments[0] == "v1" and segments[1] == "shards" and segments[3] == "pages":
            shard_id = segments[2]
            try:
                page_number = int(segments[4])
            except ValueError:
                return self._write_json({"error": "invalid page number"}, status=400)

            shard = SHARD_LOOKUP.get(shard_id)
            if shard is None:
                return self._write_json({"error": "unknown shard"}, status=404)
            if page_number < 0 or page_number >= len(shard["pages"]):
                return self._write_json({"error": "page out of range"}, status=404)

            page = shard["pages"][page_number]
            time.sleep(page["delay_ms"] / 1000.0)
            payload = {
                "shard_id": shard_id,
                "page_number": page_number,
                "records": page["records"],
                "next_page": page_number + 1 if page_number + 1 < len(shard["pages"]) else None,
            }
            return self._write_json(payload)

        return self._write_json({"error": "not found"}, status=404)

    def log_message(self, format, *args):
        return

    def _write_json(self, payload, status=200):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def running_server(host="127.0.0.1", port=0):
    server = ThreadingHTTPServer((host, port), MockShardRequestHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, name="mock-shard-api", daemon=True)
    thread.start()
    base_url = f"http://{host}:{server.server_port}"

    try:
        yield {
            "server": server,
            "thread": thread,
            "base_url": base_url,
            "fixture": FIXTURE,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)
