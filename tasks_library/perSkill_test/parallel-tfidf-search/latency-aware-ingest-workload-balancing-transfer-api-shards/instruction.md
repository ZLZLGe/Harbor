# Transfer: Latency-Aware API Shard Ingest

在 `/root/workspace/` 中，已经提供了一个本地 mock HTTP 分片服务和一个朴素轮询抓取基线：

- `/root/workspace/mock_shard_api.py`
- `/root/workspace/naive_ingest_baseline.py`

验证器会启动这个本地服务。你需要在 `/root/workspace/balanced_ingest.py` 中实现一个更均衡的并发抓取程序，从分页 API 拉取全部记录并合并输出。

你必须实现这个函数：

1. `run_balanced_ingest(base_url, output_path="/root/workspace/ingested_records.ndjson", report_path="/root/workspace/ingest_report.json", num_workers=4)`

函数要求：

- 通过 `GET {base_url}/v1/shards` 获取所有分片。
- 通过 `GET {base_url}/v1/shards/<shard_id>/pages/<page_number>` 逐页抓取数据；每个响应都会返回 `records` 和 `next_page`。
- 把所有记录写入 `output_path` 指向的 NDJSON 文件，每行一个 JSON 对象。
- NDJSON 中的记录必须按 `record_id` 升序写出。
- 同时写出 `report_path` 指向的 JSON 报告，并返回同一个报告对象。

报告 JSON 必须至少包含这些字段：

- `num_workers`
- `total_records`
- `total_pages`
- `elapsed_seconds`
- `worker_stats`

其中 `worker_stats` 必须是长度等于 `num_workers` 的列表，且每个元素都至少包含：

- `worker_id`
- `requests`
- `busy_seconds`

判定要求：

- 输出记录必须完整、无重复、无遗漏，并与服务返回的原始记录内容一致。
- `total_pages` 必须等于所有分页请求的总数。
- `worker_stats` 需要反映每个 worker 实际完成的分页请求数和 HTTP 抓取耗时。
- 某些 worker 可能在某次运行中保持空闲；只要 `worker_stats` 真实反映实际完成情况即可，不要求每个 worker 都处理到分页请求。
- 可以自由设计内部并发方式，但不要修改提供的 mock 服务或朴素基线。

性能要求：

- 使用给定服务、`num_workers=4`、各测量 3 次，与 `naive_ingest_baseline.py` 中的 `run_naive_round_robin(...)` 比较：
  - 至少 2 次总耗时快于朴素轮询版
  - 中位数总耗时不高于朴素轮询版的 `0.88x`
  - `max(worker busy_seconds) - min(worker busy_seconds)` 的中位数不高于朴素轮询版的 `0.80x`

说明：

- 可以复用基线中的 HTTP 辅助函数或输出写入逻辑。
- 只要满足输出契约和性能要求，内部实现不限。
