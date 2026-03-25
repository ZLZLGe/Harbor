你要核对一份监测名单与一份多页名录文档，输出命中索引。

输入文件：
- `/root/data/inspection_catalog`：3 页名录文档。每页正文里真正的分子条目都写成 `Entry N: <molecule>`。页眉、页脚、备注、摘要等其他行都不算条目。
- `/root/data/watchlist.txt`：待核对分子名，每行一个，文件中的顺序就是输出顺序。

请生成 `/root/workspace/watchlist_hits.json`，要求如下：

1. 输出必须是一个 JSON 数组，数组长度必须等于监测名单中的分子数。
2. 数组中每个元素都对应监测名单中的一行，顺序不得改变。
3. 每个元素必须包含以下字段：
   - `molecule`：监测名单中的原始名称。
   - `found`：布尔值，表示该分子是否在正文条目中出现过。
   - `pages`：升序整数数组，只列出该分子出现过的页码。
   - `occurrence_count`：该分子在全部正文条目中的总出现次数。
   - `page_positions`：数组，按页码升序排列。每个元素格式为 `{"page": <页码>, "positions": [<页内位置>, ...]}`。
4. `page_positions` 中的页内位置只基于该页正文里的 `Entry` 条目计算，使用 1 开始计数；如果同一页重复出现，要保留全部位置。
5. 未命中的分子必须写成：
   - `found = false`
   - `pages = []`
   - `occurrence_count = 0`
   - `page_positions = []`
6. 输出文件必须是可被标准 JSON 解析的 UTF-8 文本。
