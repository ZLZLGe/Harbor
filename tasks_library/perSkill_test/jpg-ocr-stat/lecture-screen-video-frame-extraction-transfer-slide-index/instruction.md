## 任务

`/app/workspace/lecture_assets/lecture_week3.avi` 是一段合成课程录屏，`/app/workspace/lecture_assets/lecture_capture_config.json` 给出了：

- 需要分析的视频文件名
- 固定抽样间隔（单位：秒）
- 幻灯片主画面的矩形区域坐标 `[x1, y1, x2, y2]`
- 切换预览帧输出目录
- 建议使用的变化阈值

请按配置先把录屏转换成时间序列帧，再检测真正的幻灯片切换点。录屏右侧讲师画中画和底部录制状态条会持续变化，不应被当作切换依据。

请完成两件事：

1. 为每次检测到的切换导出一张预览帧，保存到 `/app/workspace/slide_change_previews/change_<index>.jpg`。
   - `<index>` 从 `01` 开始递增。
   - 预览帧必须对应“切换后的新幻灯片”第一次被抽到的那一帧。
2. 生成 CSV 文件 `/app/workspace/slide_change_index.csv`。

CSV 必须满足以下要求：

- 使用 UTF-8 编码。
- 只能包含表头和数据行，不要有额外空行。
- 表头顺序固定为：`timestamp,preview_frame`
- `timestamp` 使用 `HH:MM:SS` 格式。
- `preview_frame` 写相对路径，格式固定为 `slide_change_previews/change_<index>.jpg`。
- 数据行按时间升序排列。
- 只记录真正发生切换的时间点，不要把 `00:00:00` 的初始幻灯片记为切换。
- 不要输出额外列。

## 说明

- 配置里的 `slide_region` 已经排除了讲师画面与底部状态条，建议优先基于该区域比较相邻抽样帧。
- 同一张幻灯片期间画面里仍会有轻微的光标移动和讲师动作，阈值不要设得过低。
