你需要根据给定输入资产，从零新建一个三页演示文稿，并保存到任务约定的固定输出路径。

环境中有两个输入文件：

- `/root/incident-brief.json`
- `/root/brand-guide.md`

请按下面要求生成 deck：

1. 文稿必须只有 3 页，顺序固定为：
   - 第 1 页：封面
   - 第 2 页：时间线
   - 第 3 页：行动表
2. 第 1 页封面必须包含：
   - 事件标题，使用 `incident-brief.json` 中的 `report_title`
   - 一行副标题，格式固定为 `severity | location | report_date`
   - `executive_summary` 的完整正文
   - 一个只显示 `severity` 文本的严重级别徽标
3. 第 2 页标题必须是 `Response timeline`，并按时间先后列出 `timeline` 数组中的全部事件。每条事件文本格式固定为 `time - event`。
4. 第 3 页标题必须是 `48-hour action tracker`，并包含一个原生 PowerPoint 表格。表头固定为 `Owner`、`Action`、`Due`、`Status`，表格数据必须完整覆盖 `actions` 数组中的全部记录。
5. 三页的标题文字都必须使用品牌主色 `#123B5D`。
6. 封面严重级别徽标的填充色必须使用品牌强调色 `#C67A2B`。
7. 输出文件必须是可打开的 PowerPoint 演示文稿，并写入任务约定的固定输出路径。

除上述硬性要求外，版式可自行组织，但内容必须准确、完整、顺序正确。
