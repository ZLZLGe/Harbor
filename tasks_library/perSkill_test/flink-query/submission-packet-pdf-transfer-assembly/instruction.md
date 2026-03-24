你会在 `/app/workspace/input/` 下拿到 4 个输入文件：

- `submission_manifest.json`：本次提交包的封面字段、页面抽取顺序和每个 section 的来源说明
- `inspection_summary.pdf`
- `effluent_monitoring.pdf`
- `training_records.pdf`

请根据 `submission_manifest.json` 组装最终提交包，并把结果写到 `/app/artifacts/regulatory_submission_packet.pdf`。

要求：

1. 先新增 1 页封面，并把它放在最终 PDF 的第一页。
2. 封面必须包含以下标签及其对应值：`Packet title`、`Packet ID`、`Applicant`、`Facility`、`Permit number`、`Submission deadline`、`Prepared by`。
3. 封面还必须包含 `Included exhibits` 小节，并按 `submission_manifest.json` 中 `assembly_order` 的顺序逐行列出，每行格式为 `<section_code>. <section_title>`。
4. 只抽取 `assembly_order` 中列出的页面，页序必须与 `assembly_order` 完全一致；不要夹带任何未列出的原始页面。
5. 如果源页面方向不正确，需要在最终提交包里修正到正常阅读方向。
6. 只交付 `/app/artifacts/regulatory_submission_packet.pdf`，不要额外输出说明文件。

我们会检查封面内容、页面顺序、页面方向，以及是否错误地保留了不该出现的原始页面。
