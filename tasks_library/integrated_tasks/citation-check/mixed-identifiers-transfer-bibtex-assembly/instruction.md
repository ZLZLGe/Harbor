你在帮助课题组整理参考文献。研究助理留下了一份混合标识符清单，其中既有 DOI、PMID、arXiv ID，也有能解析成这些标识符的论文 URL，而且其中有些行实际指向同一篇论文。

输入文件位于 `/root/mixed_identifiers.txt`。

为减少重复联网请求，环境中还提供了只读元数据快照，位于 `/root/api_cache/`。你可以直接解析这些快照，也可以自行联网核对；无论采用哪种方式，最终输出都必须来自这些标识符所对应的准确信息。

你的任务是把这份清单整理成一个规范、可直接用于 LaTeX 的 BibTeX 文件，并写入 `/root/assembled_references.bib`。

要求：
- 识别每一行的标识符类型，并抽取对应论文的准确元数据
- 如果多个标识符指向同一篇论文，只保留一个 BibTeX 条目
- citation key 必须使用 `首作者姓氏 + 年份 + 标题首个词（小写、去掉标点）` 的形式
- 条目按 citation key 的字母序排序
- 期刊或会议论文保留 `author`、`title`、`journal` 或 `booktitle`、`year`、`volume`、`number`、`pages`、`doi`、`url` 等关键信息
- DOI 字段必须写成裸 DOI，不要写成 DOI URL
- 页码范围统一写成 `--`
- 由 PMID 解析出的条目需要保留 `note = {PMID: <id>}`
- 仅有 arXiv 版本的条目使用 `@misc`，保留 arXiv URL，并在 `note` 中写 `arXiv:<id>`

不要输出额外说明，也不要生成除 `/root/assembled_references.bib` 之外的最终答案文件。
