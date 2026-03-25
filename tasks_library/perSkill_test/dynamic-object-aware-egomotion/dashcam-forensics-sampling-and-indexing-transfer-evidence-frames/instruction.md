你会拿到一段固定的行车记录仪视频、一份离散采样规格，以及一组事故时间点。任务重点不是识别事故类型，而是把每个事故时间点稳定映射到最近的合法 sample index，并导出对应证据帧。

输入资产：
- 视频：`/root/dashcam_clip.mp4`
- 采样规格：`/root/evidence_manifest.json`
- 事故时间点：`/root/incident_times.json`

请严格以 `evidence_manifest.json` 为准：
- 第 `i` 个合法样本对应的原始帧号是 `frame_id = sample_offset_frame + i * sample_stride_frames`
- `i` 的范围是 `0` 到 `sample_count - 1`
- 该样本的时间戳必须写成 `sample_timestamp_ms = round(frame_id * 1000 / video_fps)`

对 `incident_times.json` 中的每个事故时间点，选择一个最近的合法样本：
- 比较的是 `abs(event_time_ms - sample_timestamp_ms)`
- 如果有多个样本同样近，选择 `sample_index` 更小的那个
- 如果事故时间点落在采样域之外，也仍然按“最近合法样本”规则处理，因此会自然落到首端或末端样本

请输出两个结果：

1. `/root/evidence_index.json`
   - 必须是一个 JSON 对象，且只包含两个顶层键：`sampling`、`events`
   - `sampling` 必须原样回写这 4 个字段：
     - `video_fps`
     - `sample_offset_frame`
     - `sample_stride_frames`
     - `sample_count`
   - `events` 必须是数组，顺序与 `incident_times.json` 完全一致
   - `events` 中每个元素都必须是对象，且精确包含以下 6 个字段：
     - `event_id`
     - `event_time_ms`
     - `sample_index`
     - `frame_id`
     - `sample_timestamp_ms`
     - `jpeg_path`
   - `frame_id`、`sample_timestamp_ms` 和 `jpeg_path` 都必须与最终选中的 `sample_index` 一致
   - `jpeg_path` 必须写成绝对路径 `/root/evidence_frames/sample_<sample_index>.jpg`

2. `/root/evidence_frames/` 下的 JPEG 证据帧
   - 对每个被选中的不同 `sample_index`，只导出 1 张 JPEG
   - 文件名必须精确写成 `sample_<sample_index>.jpg`
   - 每张图片都必须直接来自对应的原始视频帧，不要裁剪、缩放、叠字、水印或额外留白

评测会根据输入资产重算最近样本映射，并检查：
- `evidence_index.json` 的结构、顺序和字段值是否完全正确
- 导出的 JPEG 集合是否正好对应被选中的不同 sample index
- 每张 JPEG 是否确实来自它声明的那一帧
