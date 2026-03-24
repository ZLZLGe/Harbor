你要为馆藏编目项目清洗一份杂乱的 BibTeX 参考文献。

请先阅读 `/root/archive_catalog_raw.bib`，然后把整理后的结果写入 `/root/exhibit_catalog_clean.bib`。

处理规则：

- 先做 DOI 规范化，再据此去重；规范化后 DOI 相同的条目视为重复
- 如果重复组里同时存在 key 以 `Draft`、`Copy` 或 `Dup` 结尾的版本，优先丢弃这些后缀版本
- 条目按 citation key 的字母序排序
- 只保留下列字段，且字段顺序必须严格一致：
  - `@article`: `author`, `title`, `journal`, `year`, `volume`, `number`, `pages`, `doi`
  - `@inproceedings`: `author`, `title`, `booktitle`, `year`, `pages`, `doi`
  - `@book`: `author`, `title`, `publisher`, `year`, `address`, `edition`, `isbn`
- 规范化细节：
  - 作者分隔符中的 `;` 和 `&` 统一改为 `and`
  - 页码去掉 `pp.` 前缀，并把单连字符页码范围改成 `--`
  - DOI 去掉 `https://doi.org/`、`http://doi.org/` 和 `doi:` 前缀
  - 删除不在允许列表里的字段
- 保留原始题名大小写与标点，不要补全不存在的元数据
- 不要联网，不要生成其他文件，也不要输出额外说明
