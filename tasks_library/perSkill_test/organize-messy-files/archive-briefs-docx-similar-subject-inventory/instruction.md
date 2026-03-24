你在整理编辑部的收件箱。

`/root/inbox/` 里有 8 份 Word 稿件，文件名都比较随意，必须根据文档正文判断它们属于哪个主题。请把每份稿件移动到 `/root/desks/` 下已经建好的 4 个目录之一：

- `climate_transition`
- `consumer_ai`
- `public_health`
- `urban_mobility`

要求：

- 每份稿件只能归入一个目录。
- 保持文档内容和文件名不变。
- 完成后，`/root/inbox/` 中不能再剩下任何 Word 稿件。
- 生成 `/root/subject_inventory.json`，内容必须是一个 JSON 对象，并且只包含以上 4 个目录名作为键。
- JSON 中每个键对应的值是该目录内最终文件名组成的数组，数组按文件名字典序排序。

除了这 4 个主题目录和 JSON 清单外，不需要产出其他结果。
