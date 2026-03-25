你需要把一份不可填写的现场巡检表按给定答案标注完成。

输入文件：
- `/root/inspection_answers.json`：本次巡检的结构化答案。
- `/root/` 下还提供了一份两页静态巡检表原始文档，文件名以 `inspection_form` 开头；它没有可填写字段。

任务目标：
- 在原表单上直接添加可见文字和勾选标记，并把结果写到任务元数据指定的主输出文件。

填写规则：
- 输出必须保留原始 2 页，不要重建成新模板，也不要把整页栅格化成图片后重新导出。
- 新增的可见填写项只应包含以下内容：`site_name`、`inspection_date`、`inspector`、`permit_number`、`pump_station_id`、`pressure_psi`、`action_notes`，以及 `shift`、`weather`、6 个布尔检查项所需的勾选标记。
- 每个需要填写的位置只添加一次有效内容，不要重复叠写，也不要增加无关可见文本或勾选。
- 这些字段必须以可见文字写入对应空白区域：`site_name`、`inspection_date`、`inspector`、`permit_number`、`pump_station_id`、`pressure_psi`、`action_notes`。
- `pressure_psi` 只写数值本身，不要额外加单位。
- `shift` 只能在 `Day` 或 `Night` 中勾选一个，用可见的 `X` 标记对应方框。
- `weather` 只能在 `Clear`、`Rain`、`Windy` 中勾选一个，用可见的 `X` 标记对应方框。
- `inspection_answers.json` 里的 `checks` 对象包含 6 个布尔值。值为 `true` 时勾选对应的 `Yes` 方框，值为 `false` 时勾选对应的 `No` 方框。
- 所有未被选中的方框必须保持空白，不能同时勾选同一组里的两个选项。
- `action_notes` 必须完整可见，并且留在第 2 页的 notes 方框内。
- 评测会逐项核对新增可见内容是否出现在对应页面和对应填写区域内，但不要求使用特定的底层实现方式。

除了主输出文件以外，不要求输出其他文件。
