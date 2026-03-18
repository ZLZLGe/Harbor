你要在投稿前帮研究团队做一次参考文献完整性审计。

待审查的 BibTeX 文件位于 `/root/manuscript_refs.bib`。请检查每个条目，找出以下三类问题：

- `invalid_doi`: DOI 无法解析或明显无效
- `metadata_mismatch`: DOI 能解析，但返回的核心元数据与 BibTeX 条目明显不匹配
- `missing_required_fields`: 缺少该条目类型的必填字段

将结果写入 `/root/bibliography_audit.json`，格式必须为：

```json
{
  "audited_file": "/root/manuscript_refs.bib",
  "total_entries": 7,
  "flagged_entry_count": 4,
  "flagged_entries": [
    {
      "citation_key": "example2024",
      "title": "Clean Title",
      "issue_types": ["invalid_doi"],
      "missing_fields": [],
      "notes": ["Brief evidence for the finding."]
    }
  ]
}
```

要求：

- `flagged_entries` 里只保留存在问题的条目
- `citation_key` 按字母序排序
- `issue_types` 只能使用上面 3 个标签，去重后按字母序排序
- `missing_fields` 只列出缺失的必填字段名；如果没有缺失字段，返回空数组
- `notes` 需要给出简短证据；如果问题与 DOI 有关，说明你核查过的 DOI
- `title` 需要清理掉 BibTeX 格式字符，例如 `{}` 或反斜杠
- 不要输出额外文件，也不要在 JSON 之外附加说明
