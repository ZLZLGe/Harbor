## 任务说明

`/app/input/feeds/` 下提供了多段人行道监控视频，目录中可能包含多级子目录。请递归读取其中所有 `.mp4` 文件，对每个视频按固定时间间隔抽帧，并生成一份供人工复核使用的 JSON 清单。

## 你需要产出

1. 在 `/app/output/surveillance_sampling_manifest.json` 写入一个 UTF-8 JSON 文件。
2. 在 `/app/output/review_frames/` 下为每个视频创建一个独立子目录，并把对应抽取出的 JPEG 帧写进去。

## 抽帧规则

- 只处理 `/app/input/feeds/` 下的 `.mp4` 文件，且需要递归遍历子目录。
- 对每个视频从 `0.0` 秒开始抽帧，之后每隔 `2.0` 秒再抽 1 帧。
- 只保留时间点严格小于视频时长的抽样点。
- 同一个视频的抽样时间点必须按升序排列。
- JPEG 文件名固定为 `frame_0000.jpg`、`frame_0001.jpg`、`frame_0002.jpg` 这样的四位连续编号。

## JSON 清单格式

顶层对象必须包含以下字段：

- `sampling_interval_seconds`: 固定写为 `2`
- `video_count`: 处理到的视频数量
- `total_extracted_frames`: 所有视频抽取帧数总和
- `videos`: 数组，按 `source_file` 升序排列

`videos` 数组中的每个对象必须包含以下字段：

- `source_file`: 源视频相对 `/app/input/` 的相对路径，例如 `feeds/camera_north/weekday_sidewalk.mp4`
- `fps`: 源视频帧率，使用 JSON 数值
- `frames_dir`: 当前视频帧目录相对 `/app/output/` 的相对路径，格式为 `review_frames/<源视频相对 feeds/ 的路径去扩展名>`；例如 `feeds/camera_north/weekday_sidewalk.mp4` 对应 `review_frames/camera_north/weekday_sidewalk`
- `extracted_count`: 当前视频抽取出的 JPEG 数量
- `samples`: 数组，按时间升序排列

`samples` 数组中的每个对象必须包含以下字段：

- `timestamp_seconds`: 该帧对应的抽样时间点，使用 JSON 数值
- `relative_path`: 该 JPEG 相对 `/app/output/` 的相对路径

## 其他要求

- `frames_dir` 中列出的 JPEG 文件都必须真实存在。
- `relative_path` 必须指向对应视频自己的帧目录内文件。
