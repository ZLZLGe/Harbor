圆桌访谈的上游处理已经完成，输入文件 `/root/panel_segments.json` 中给出了每个语音片段的起止时间和对应说话人嵌入。你需要仅基于这些片段信息重建可评分的 RTTM。

请完成以下目标：

1. 读取 `/root/panel_segments.json`。
2. 自动估计这段访谈里有多少位说话人，并对全部片段做聚类。
3. 对时间上相邻且被分到同一类的片段进行合并；合并阈值请使用输入文件中的 `merge_gap_sec`。
4. 将最终话轮写入 `/root/panel_diarization.rttm`。

输出要求：

- RTTM 的 `file_id` 必须使用输入里的 `session_id`。
- 说话人标签请使用统一的简洁格式，例如 `spk00`、`spk01`。
- 每一行都必须是标准 RTTM `SPEAKER` 记录，包含开始时间和持续时长。
- 最终结果中，不应再出现“相邻且同一说话人、且间隔不超过 `merge_gap_sec`”但仍未合并的条目。

示例格式：

```text
SPEAKER panel_roundtable 1 0.000000 1.880000 <NA> <NA> spk00 <NA> <NA>
SPEAKER panel_roundtable 1 2.200000 1.520000 <NA> <NA> spk01 <NA> <NA>
```
