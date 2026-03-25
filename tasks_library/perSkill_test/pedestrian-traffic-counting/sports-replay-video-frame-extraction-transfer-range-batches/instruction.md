## 任务说明

`/app/input/replay_ranges.csv` 给出了多段体育回放片段配置，`/app/input/videos/` 下提供了对应的比赛视频。请按配置逐段抽取指定帧区间，并整理成 PNG 序列和汇总 CSV，供后续视频归档使用。

## 你需要产出

1. 在 `/app/output/replay_range_summary.csv` 写出 UTF-8 编码的 CSV 汇总表。
2. 在 `/app/output/replay_batches/` 下为每个片段创建独立目录，并写入对应的 PNG 帧。

## 输入配置

`/app/input/replay_ranges.csv` 包含以下表头：

- `clip_id`
- `source_video`
- `start_frame`
- `end_frame`

每一行表示一个要处理的回放片段。

## 抽帧规则

- 只处理配置文件中列出的片段，且按配置文件中的行顺序输出汇总表。
- `start_frame` 和 `end_frame` 都是基于源视频的 0 开始帧编号，并且区间两端都要包含。
- 每个片段的输出目录固定为 `/app/output/replay_batches/<clip_id>/`。
- 对于区间内的每一帧，都要输出一个 PNG 文件。
- PNG 文件名固定为 `frame_<源帧编号六位补零>.png`，例如源帧编号为 `12` 时文件名应为 `frame_000012.png`。
- 每个片段目录中只应包含该片段区间内的 PNG 文件。

## 汇总 CSV 格式

`/app/output/replay_range_summary.csv` 必须只有以下六列，且表头顺序固定：

- `clip_id`
- `source_video`
- `start_frame`
- `end_frame`
- `frames_written`
- `output_dir`

其中：

- `frames_written` 等于该片段实际落盘的 PNG 数量。
- `output_dir` 是相对 `/app/output/` 的相对路径，格式固定为 `replay_batches/<clip_id>`。
- 每个数据行都应与输入配置中的一行片段一一对应。

## 其他要求

- 所有汇总表中列出的目录和 PNG 文件都必须真实存在。
- 不要生成题目未要求的主输出文件路径。
