# Similar: Python JSONL Audit Event Normalizer

请把 `/root/EventNormalizer.py` 翻译成 Scala 2.13，并将结果保存为 `/root/EventNormalizer.scala`。

你的 Scala 代码需要保留并实现这些公开类型与行为：

- `AuditEvent`
- `EventSummary`
- `EventNormalizer`
- `parseLine`
- `normalizeTimestamp`
- `extractLabels`
- `normalizeEvent`
- `loadEvents`
- `summarize`
- `normalizeFile`
- `loadAndSummarize`

行为要求如下：

- 继续读取和解析 JSONL 审计事件。
- 将多种时间格式统一标准化为 UTC 的 ISO-8601 字符串，格式为 `yyyy-MM-ddTHH:mm:ssZ`。
- 从资源名和说明文本中提取 `#label` 标签，转为小写并去重，同时保留首次出现顺序。
- 根据事件动作和说明文本判断风险级别。
- 支持批量加载、写出归一化后的 JSONL，并返回汇总结果。

不要逐字照搬 Python 结构；请写成符合 Scala 2.13 习惯、可读且可维护的实现，并确保能够通过环境中的测试。
