# Transfer: Size-Aware Genome K-mer Counting

在 `/root/workspace/` 中，已经提供了一组基因序列输入资产和一个朴素并行基线：

- `/root/workspace/genome_manifest.json`
- `/root/workspace/genomes/`
- `/root/workspace/kmer_counter_baseline.py`

这些 FASTA 文件混合了大量短读段和少数超长片段。你需要在 `/root/workspace/kmer_counter_balanced.py` 中实现一个更合理的并行 k-mer 统计程序，在保持结果完全一致的同时，尽量避免某个 worker 因为拿到超长序列而拖慢总耗时。

你必须实现这个函数：

1. `count_kmers_balanced(fasta_paths=None, k=6, output_path="/root/workspace/kmer_counts.json", report_path="/root/workspace/kmer_report.json", num_workers=2)`

函数要求：

- 当 `fasta_paths` 为 `None` 时，默认使用 `genome_manifest.json` 中列出的全部 FASTA 文件。
- 读取所有序列记录，对全部窗口做普通 k-mer 计数；题目提供的序列都只包含 `A/C/G/T`，不需要做额外模糊字符处理。
- 将结果写入 `output_path` 指向的 JSON 文件，并返回报告对象。
- 同时将报告写入 `report_path` 指向的 JSON 文件，返回值必须与写入文件内容一致。

计数输出 JSON 必须至少包含这些字段：

- `k`
- `total_sequences`
- `counts`

其中 `counts` 必须是完整的 k-mer -> 计数映射，语义上必须与顺序基线完全一致。

报告 JSON 必须至少包含这些字段：

- `k`
- `num_workers`
- `total_sequences`
- `total_bases`
- `distinct_kmers`
- `elapsed_seconds`
- `worker_stats`

其中 `worker_stats` 必须是长度等于 `num_workers` 的列表；每个元素都至少包含：

- `worker_id`
- `sequence_count`
- `base_load`
- `kmers_emitted`

判定要求：

- 所有 k-mer 计数必须与顺序基线逐项完全一致。
- `total_sequences`、`total_bases` 和 `distinct_kmers` 必须与真实输入一致。
- `worker_stats` 需要反映每个 worker 实际处理到的序列条数、累计碱基数和发出的 k-mer 窗口数。

性能要求：

- 使用给定输入、`num_workers=2`、`k=6`，与 `kmer_counter_baseline.py` 中的 `run_naive_equal_split(...)` 比较，测量 3 次。
  验证器会独立用 wall-clock 计时整个函数调用，不以报告中的 `elapsed_seconds` 作为性能判定依据：
  - 至少 2 次总耗时快于朴素等量切片版
  - 总耗时中位数不高于朴素版的 `0.85x`
- 在同一组输入上，`max(worker base_load) - min(worker base_load)` 必须不高于朴素版的 `0.25x`。

说明：

- 可以复用基线中的 FASTA 解析、输出写入或局部计数辅助函数。
- 只要满足输出契约和性能要求，内部并行方式不限。
