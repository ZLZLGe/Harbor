# Similar: Memory-Bounded TF-IDF Search Pipeline

在 `/root/workspace/` 里有一个归档检索脚本 `archive_search_baseline.py`。它会读取一份 JSONL 语料和一份查询列表，计算 TF-IDF，并输出检索报告；但是它会把多份重复中间结构整批放进内存，在大语料上峰值内存过高。

请你重写这条流水线，并把答案写到 `/root/workspace/memory_search_solution.py`。

你的脚本必须支持下面的命令行接口：

```bash
python /root/workspace/memory_search_solution.py \
  --corpus /path/to/corpus.jsonl \
  --queries /path/to/queries.json \
  --output /path/to/report.json \
  --top-k 5
```

你可以自由决定内部实现，但必须满足这些约束：

1. 必须复现 `archive_search_baseline.py` 的文本处理与 TF-IDF 语义：
   - 分词规则：小写后按正则 `\b[a-z]{2,}\b` 提取 token
   - 过滤同一份停用词集合
   - TF = `term_count / total_tokens`
   - IDF = `log(N / df) + 1`
2. 输出 JSON 必须写到 `--output` 指定路径，结构必须是：

```json
{
  "corpus": {
    "num_documents": 0,
    "vocabulary_size": 0,
    "num_postings": 0
  },
  "queries": [
    {
      "query_id": "Q1",
      "query": "example query",
      "results": [
        {
          "doc_id": 0,
          "headline": "Example headline",
          "score": 0.0
        }
      ]
    }
  ]
}
```

3. `corpus` 下的三个统计值必须与基线完全一致：
   - `num_documents`: 文档总数
   - `vocabulary_size`: 词表大小
   - `num_postings`: 所有文档中“去重 term 数”的总和
4. 每条查询的结果必须与基线完全一致：
   - 只返回 `top-k`
   - 先按 `score` 降序，再按 `doc_id` 升序
   - `score` 写入 JSON 时必须保留 12 位小数精度（四舍五入后的数值写入）
5. 在评测提供的 full archive fixture 上，运行你的脚本时最大 RSS 不能超过 `350 MB`。
6. 可以使用 `/tmp` 存放临时文件，但最终只需要提交 `/root/workspace/memory_search_solution.py`。

可用输入资产：

- `/root/workspace/archive_search_baseline.py`
- `/root/workspace/archive_fixture.py`
- `/root/workspace/archive_queries.json`

评测会在不同规模的归档语料上运行你的脚本，并核对输出报告与内存占用。
