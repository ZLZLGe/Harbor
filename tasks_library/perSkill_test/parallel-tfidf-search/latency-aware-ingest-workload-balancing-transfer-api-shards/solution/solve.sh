#!/bin/bash
set -euo pipefail

cat > /root/workspace/balanced_ingest.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import queue
import threading
import time
from pathlib import Path

from naive_ingest_baseline import fetch_page, list_shards


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


def run_balanced_ingest(
    base_url,
    output_path="/root/workspace/ingested_records.ndjson",
    report_path="/root/workspace/ingest_report.json",
    num_workers=4,
):
    shard_entries = list_shards(base_url)
    task_queue = queue.Queue()
    for entry in shard_entries:
        task_queue.put((entry["shard_id"], 0))

    worker_stats = [
        {"worker_id": worker_id, "requests": 0, "busy_seconds": 0.0}
        for worker_id in range(num_workers)
    ]
    records = []
    records_lock = threading.Lock()

    def worker(worker_id):
        while True:
            task = task_queue.get()
            if task is None:
                task_queue.task_done()
                return

            shard_id, page_number = task
            started = time.perf_counter()
            payload = fetch_page(base_url, shard_id, page_number)
            elapsed = time.perf_counter() - started

            worker_stats[worker_id]["requests"] += 1
            worker_stats[worker_id]["busy_seconds"] += elapsed

            with records_lock:
                records.extend(payload["records"])

            next_page = payload["next_page"]
            if next_page is not None:
                task_queue.put((shard_id, next_page))

            task_queue.task_done()

    start_time = time.perf_counter()
    threads = [
        threading.Thread(target=worker, args=(worker_id,), name=f"balanced-worker-{worker_id}")
        for worker_id in range(num_workers)
    ]
    for thread in threads:
        thread.start()

    task_queue.join()
    for _ in range(num_workers):
        task_queue.put(None)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output-path", default="/root/workspace/ingested_records.ndjson")
    parser.add_argument("--report-path", default="/root/workspace/ingest_report.json")
    parser.add_argument("--num-workers", type=int, default=4)
    args = parser.parse_args()

    report = run_balanced_ingest(
        args.base_url,
        output_path=args.output_path,
        report_path=args.report_path,
        num_workers=args.num_workers,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
PY

chmod +x /root/workspace/balanced_ingest.py
