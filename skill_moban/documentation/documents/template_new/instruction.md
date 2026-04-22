你正在支持采购法务运营团队完成一份即将发给供应商的 Word 增补协议定稿。团队已经给出了带红线的 `.docx` 文档和审阅决定，但当前文件仍保留了 tracked changes、review comments，以及包内待定稿的结构化审阅元数据，不能直接发给对方签署。

输入数据在：
- `/app/vendor_addendum_redline.docx`
- `/app/review_decisions.json`

你的任务
1、根据 `review_decisions.json` 中的审阅决定，处理 `vendor_addendum_redline.docx` 中对应的红线修改。
2、每一项修改都需要根据决定执行 `accept` 或 `reject`，并生成干净的最终版 Word 文档。
3、最终文档中不能保留 tracked changes、review comments、comment markers 或其他审阅痕迹。
4、保持原始文档的整体结构与版式，包括页眉、页脚、正文段落、脚注和表格，不要把文档改写成纯文本导出，也不要替换成 PDF 或其他格式。
5、文档包内与审阅链路相关的结构化内容也必须和最终可见内容一致，不能只修可见层而忽略 `customXml`、脚注或其他包内数据。
6、将最终结果保存到 `/app/output/vendor_addendum_final.docx`。

输出格式：
- 生成文件：
  - `/app/output/vendor_addendum_final.docx`

说明：
- 输出必须是一个真实可打开的 `.docx` 文件。
- 最终文档中不能残留任何审阅标记、评论引用、占位性质的 review 文本或 pending 审阅状态。
- 你可以编写辅助脚本处理 DOCX 包，但最终验收文件只有 `/app/output/vendor_addendum_final.docx`。
- 不要 hack verifier，不要根据测试文件硬编码答案。
- 不要通过删除表格、删除页眉页脚、删除脚注、删除结构化 review 部件、重建一个极简新文档、或替换真实文档链路来规避任务。
- 不要修改输入文档、输入 JSON、测试文件、依赖配置或任何 skill 文件。
