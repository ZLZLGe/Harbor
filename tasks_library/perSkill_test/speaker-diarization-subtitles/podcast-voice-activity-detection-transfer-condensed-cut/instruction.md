处理 `/root/raw_podcast.wav`，按 `/root/edit_policy.json` 自动去掉长时间 dead-air，只保留明显有人声的内容，并导出压缩后的成片 `/root/condensed_podcast.wav`。

同时写出一个裁切报告 `/root/condense_report.json`。

要求：

- 先定位原音频中明显包含人声的区间；纯静音、底噪、房间嗡声都不应单独保留。
- 读取 `/root/edit_policy.json`：
  - 如果两个有人声区间之间的间隔不超过 `merge_gap_seconds`，把它们视为同一段内容。
  - 对每个最终保留段的前后各补上 `padding_seconds`，但不能越过音频边界。
- 将所有最终保留段按原顺序首尾拼接到同一个输出文件中，不要改变片段顺序，也不要在片段之间额外插入空白。
- 输出 WAV 必须是单声道、16 kHz、16-bit PCM。
- 允许边界相对理想语音起止存在最多 `0.08` 秒误差，但不要明显截掉整句主体，也不要把长静音带进结果。

`/root/condense_report.json` 必须是一个 JSON 对象，格式如下：

```json
{
  "source_file": "/root/raw_podcast.wav",
  "output_file": "/root/condensed_podcast.wav",
  "kept_regions": [
    {
      "start": 0.42,
      "end": 3.38,
      "duration": 2.96
    }
  ],
  "summary": {
    "segment_count": 1,
    "input_duration_sec": 15.5,
    "output_duration_sec": 2.96,
    "removed_silence_sec": 12.54,
    "merge_gap_seconds": 0.28,
    "padding_seconds": 0.08
  }
}
```

补充约束：

- 所有时间单位都是秒，数值保留到 3 位小数以内即可。
- `kept_regions` 必须按 `start` 升序排列，且片段之间不能重叠。
- 每个片段都必须包含 `start`、`end`、`duration`，并满足 `duration = end - start`。
- `summary.segment_count` 必须等于 `kept_regions` 的长度。
- `summary.output_duration_sec` 应与输出音频的实际时长一致，误差不超过 `0.02` 秒。
