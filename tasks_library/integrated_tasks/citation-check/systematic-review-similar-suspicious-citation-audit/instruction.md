你在帮助一个研究团队核验系统综述附录中的参考文献。团队提供了一份混合 BibTeX 文件，其中包含期刊论文、会议论文、预印本和书籍条目；他们怀疑其中有些标题是伪造的、幻觉生成的，或无法在主流学术数据库中核实。

输入文件位于 `/root/appendix_references.bib`。

你的任务是识别所有可疑条目的标题，并把结果写入 `/root/fake_citation_titles.json`。

输出文件必须是一个 JSON 字符串数组，例如：

```json
[
  "First suspicious title",
  "Second suspicious title"
]
```

要求：
- 只返回可疑或无法核实的条目标题，不要返回 citation key
- 标题需要清洗，去掉 BibTeX 中的 `{}`、反斜杠等格式化痕迹
- 结果按字母序排序
- 不要因为条目缺少 DOI 就直接判定为可疑；书籍和预印本也需要按标题、作者、出版信息等交叉核验
