你会拿到三个输入文件：

- `/root/practice_review_feed.mp4`
- `/root/coaching_bug.png`
- `/root/replay_spec.json`

请生成 `/outputs/coaching-replay.mp4`。

交付规格如下：

1. 成片必须是静音回放，只保留视频流，不要保留任何音频轨道，也不要额外生成别的文件。
2. `/root/replay_spec.json` 给出了要截取的单段回放时间窗。输出只包含这一个时间窗对应的内容，不要保留片头、片尾或原片里的其他时段。
3. 先按 `replay_spec.json` 中的 `crop_width_expr`、`crop_height_expr`、`crop_x_expr`、`crop_y_expr` 裁出动作分析区域，再缩放到 `output_width` 和 `output_height`；整段回放都要保持这个固定取景。
4. 这段回放需要整体放慢，输出时长必须变成该时间窗原始时长乘以 `slowdown_factor`，用于教练复盘。
5. 把 `/root/coaching_bug.png` 缩放到 `logo_width` 指定的宽度后，按 `overlay_x`、`overlay_y` 叠加到成片右上区域，透明度保持输入图本身的效果。
6. 除 `/outputs/coaching-replay.mp4` 外，不需要生成其他文件，也不要改动输入资产。
