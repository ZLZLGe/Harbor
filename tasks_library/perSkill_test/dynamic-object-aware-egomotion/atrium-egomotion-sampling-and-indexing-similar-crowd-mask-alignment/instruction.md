你会在 `/root/` 下看到一段中庭手持视频 `input.mp4`，以及人工整理好的源帧级辅助标注文件 `atrium_annotations.json`。

请只在采样帧索引空间内生成以下两个结果：

1. `/root/pred_camera_intervals.json`
   - 记录相机运动区间。
   - 键必须严格写成 `start->end`，其中 `start` 和 `end` 都是整数采样索引，`end` 为开区间边界。
   - 值是 motion label 数组，合法标签只有：
     - `Stay`
     - `Dolly In`
     - `Dolly Out`
     - `Pan Left`
     - `Pan Right`
     - `Tilt Up`
     - `Tilt Down`
     - `Roll Left`
     - `Roll Right`

2. `/root/pred_crowd_masks.npz`
   - 记录每个采样帧的人群二值掩码。
   - 掩码分辨率写在 `shape` 键下，格式是 `[H, W]`。
   - 每个采样帧 `i` 的掩码都要用 CSR 稀疏格式保存为三组键：
     - `f_{i}_data`
     - `f_{i}_indices`
     - `f_{i}_indptr`

补充要求：

- 这段视频按 7fps 采样，采样帧索引从 0 开始。
- `atrium_annotations.json` 里已经给出了这次任务应使用的 `sample_source_frames`，它们定义了每个采样索引对应的源帧编号。
- `camera_segments` 和 `crowd_segments` 都是源帧编号空间下的半开区间 `[start_frame, end_frame)`。
- 两份输出必须覆盖同一批采样帧；不要多写，也不要少写。
- 最终区间必须基于采样索引连续合并，不能保留源帧编号。
