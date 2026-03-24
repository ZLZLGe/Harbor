## 任务

`/app/workspace/assembly_line_assets/line_patrol.avi` 是一段饮料产线巡检视频，`/app/workspace/assembly_line_assets/cap_audit_config.json` 给出了：

- 需要分析的视频文件名
- 固定抽样节拍（单位：秒）
- 传送带审计区域坐标 `[x1, y1, x2, y2]`
- 抽样区域帧输出目录
- 输出工作表名称

请从 `0` 秒开始，严格按配置中的固定节拍抽样，并只保留传送带审计区域。

你需要完成两件事：

1. 将每个节拍对应的传送带区域帧保存到 `/app/workspace/cap_audit_frames/beat_<index>.jpg`。
   - `<index>` 从 `01` 开始递增。
   - 保存的是裁剪后的传送带区域，而不是整帧画面。
2. 生成 Excel 文件 `/app/workspace/cap_audit.xlsx`。

Excel 必须满足以下要求：

- 只能包含一个 sheet，名称固定为 `audit`。
- 第一行必须是表头，列顺序固定为：
  - `beat_index`
  - `timestamp`
  - `frame_file`
  - `red_caps`
  - `blue_caps`
  - `total_caps`
- 明细行必须按抽样时间升序排列。
- `beat_index` 从 `1` 开始递增。
- `timestamp` 使用 `HH:MM:SS` 格式。
- `frame_file` 写相对路径，格式固定为 `cap_audit_frames/beat_<index>.jpg`。
- `red_caps` 和 `blue_caps` 分别是该节拍区域帧中红盖瓶与蓝盖瓶的数量。
- `total_caps` 必须等于 `red_caps + blue_caps`。
- 明细行之后必须追加且只追加一行汇总行：
  - `beat_index` 固定写 `TOTAL`
  - `timestamp` 与 `frame_file` 留空
  - `red_caps`、`blue_caps`、`total_caps` 分别写所有明细行对应列的总和
- 不要生成额外的列、空行或额外 sheet。

## 说明

- 画面中传送带外还会出现颜色提示灯和设备面板，不属于统计对象。
- 只统计传送带审计区域里清晰可见的瓶盖；瓶身和背景不应计入颜色数量。
