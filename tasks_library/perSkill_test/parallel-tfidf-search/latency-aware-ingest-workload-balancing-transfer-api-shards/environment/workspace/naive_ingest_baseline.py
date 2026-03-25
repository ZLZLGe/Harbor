#!/usr/bin/env python3

import json
import threading
import time
import urllib.request
from pathlib import Path


def _get_json(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def list_shards(base_url):
    payload = _get_json(f"{base_url}/v1/shards")
    return payload["shards"]


def fetch_page(base_url, shard_id, page_number):
    return _get_json(f"{base_url}/v1/shards/{shard_id}/pages/{page_number}")


def _write_outputs(records, output_path, report_path, report):
    output_file = Path(output_path)
    report_file = Path(report_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.parent.mkdir(parents=True, exist_ok=True)

    sorted_records = sorted(records, key=lambda item: item["record_id"])
    with output_file.open("w", encoding="utf-8") as handle:
        for record in sorted_records:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")

    with report_file.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)


def run_naive_round_robin(
    base_url,
    output_path="/root/workspace/naive_ingested_records.ndjson",
    report_path="/root/workspace/naive_ingest_report.json",
    num_workers=4,
):
    shard_entries = list_shards(base_url)
    shard_ids = [entry["shard_id"] for entry in shard_entries]

    assignments = [[] for _ in range(num_workers)]
    for index, shard_id in enumerate(shard_ids):
        assignments[index % num_workers].append(shard_id)

    worker_stats = [
        {"worker_id": worker_id, "requests": 0, "busy_seconds": 0.0}
        for worker_id in range(num_workers)
    ]
    records = []
    records_lock = threading.Lock()

    def worker(worker_id):
        for shard_id in assignments[worker_id]:
            page_number = 0
            while True:
                started = time.perf_counter()
                payload = fetch_page(base_url, shard_id, page_number)
                elapsed = time.perf_counter() - started
                worker_stats[worker_id]["requests"] += 1
                worker_stats[worker_id]["busy_seconds"] += elapsed
                with records_lock:
                    records.extend(payload["records"])
                next_page = payload["next_page"]
                if next_page is None:
                    break
                page_number = next_page

    start_time = time.perf_counter()
    threads = [
        threading.Thread(target=worker, args=(worker_id,), name=f"naive-worker-{worker_id}")
        for worker_id in range(num_workers)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    elapsed_seconds = time.perf_counter() - start_time

    report = {
        "num_workers": num_workers,
        "total_records": len(records),
        "total_pages": sum(worker["requests"] for worker in worker_stats),
        "elapsed_seconds": elapsed_seconds,
        "worker_stats": worker_stats,
    }
    _write_outputs(records, output_path, report_path, report)
    return report
