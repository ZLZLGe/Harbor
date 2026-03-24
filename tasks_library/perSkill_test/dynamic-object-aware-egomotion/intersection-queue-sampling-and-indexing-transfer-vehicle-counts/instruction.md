给定固定机位路口视频 `/root/input.mp4`，请按 `fps = 3` 做固定速率采样，并输出一个 CSV 文件 `/root/pred_queue_counts.csv`。

CSV 必须严格包含这 3 列，列名也必须一致：

- `sample_index`
- `source_frame_id`
- `queued_vehicle_count`

要求如下：

- `sample_index` 从 `0` 开始连续编号，表示采样后的样本序号。
- `source_frame_id` 表示这个样本对应的原始视频帧号，不是时间戳。
- `queued_vehicle_count` 表示该采样帧里，北向来车在停止线前已经排队等待的车辆数。
- 只统计停止线前、位于主车道中的排队车辆，不要把横向穿行车辆、已经越过停止线的车辆或路边背景元素算进去。
- 每个采样帧都要恰好输出一行，行顺序必须按 `sample_index` 递增。

示例格式：

```csv
sample_index,source_frame_id,queued_vehicle_count
0,0,1
1,4,2
```
