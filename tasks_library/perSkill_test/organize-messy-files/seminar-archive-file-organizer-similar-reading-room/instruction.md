整理 `/root/seminar_drop/inbox/` 里的混杂研讨资料。这里有一批学术 PDF、讲义 DOCX 和汇报 PPTX，分别属于 4 个主题：

1. `causal_inference`
2. `field_robotics`
3. `climate_transition`
4. `graph_learning`

请根据文件内容，把每个文件移动到 `/root/seminar_drop/organized/<topic>/` 下对应的主题目录中。每个文件只能归入一个主题，不要修改文件名，也不要修改文件内容。

完成整理后，还需要生成 `/root/seminar_drop/reports/placement_manifest.json`。这个 JSON 文件必须是一个按 `file_name` 升序排列的数组；数组中的每个对象必须包含以下字段：

- `file_name`
- `category`
- `source`
- `destination`
- `sha256`

其中：

- `source` 必须是文件整理前在 inbox 中的绝对路径。
- `destination` 必须是文件整理后的绝对路径。
- `sha256` 必须和最终归档文件的实际 SHA-256 一致。

整理完成后，`/root/seminar_drop/inbox/` 中不应再留下任何这批资料文件。
