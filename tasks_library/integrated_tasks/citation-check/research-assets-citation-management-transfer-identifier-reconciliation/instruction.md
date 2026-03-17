你要帮研究资料管理员整理一份混合标识符清单，并生成可直接归档的核对结果。

请先阅读：

- `/root/research_assets.txt`
- `/root/record_snapshot.json`

`/root/research_assets.txt` 是待核对的原始输入，每行一项，混合了 DOI、PMID、arXiv ID 和论文链接。`/root/record_snapshot.json` 是当前项目可用的权威记录快照。你的任务是把每条输入和快照中的记录进行对账，并把结果写入 `/root/asset_resolution.json`。

输出必须是 JSON 对象，且只包含两个顶层字段：

- `resolved_records`
- `unverified_items`

其中：

- `resolved_records` 是数组，按 `canonical_id` 字母序排序
- 每个 resolved record 必须包含以下字段：
  - `canonical_id`
  - `title`
  - `year`
  - `matched_inputs`
  - `identifiers`
- `canonical_id`、`title`、`year` 和 `identifiers` 必须直接来自快照，不要自创
- `matched_inputs` 必须保留原始输入字符串，并按它们在 `research_assets.txt` 中首次出现的顺序排列
- `identifiers` 必须是对象，且固定包含这四个键：
  - `doi`
  - `pmid`
  - `arxiv`
  - `url`
- 对于快照中不存在的标识符，使用 `null`

- `unverified_items` 是数组，按原始输入出现顺序排列
- 每个 unverified item 必须包含：
  - `input`
  - `reason`
- 本任务里无法和快照中任何记录对上的输入，`reason` 统一写成 `no_matching_record`

额外要求：

- 每条原始输入必须且只能出现在一个位置：要么归入某个 `resolved_records[*].matched_inputs`，要么出现在 `unverified_items`
- 允许通过 DOI/PMID/arXiv/链接中的可提取标识符进行匹配
- 不要输出额外说明，不要生成其他文件
