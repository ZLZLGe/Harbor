# 任务说明

近岸试验的一段单通道水听器录音里混入了 3 次线性调频脉冲，三种参考脉冲都已给出，并且每种脉冲在录音中恰好出现一次。请直接使用文件中的样本值做滑动内积扫描，找出每种脉冲的最佳响应位置，并把结果写到 `/root/hydrophone_ping_report.csv`。

输入文件：

- `/root/data/hydrophone_recording.wav`：单通道 16-bit PCM WAV 录音。
- `/root/data/reference_chirps/ping_alpha.csv`
- `/root/data/reference_chirps/ping_bravo.csv`
- `/root/data/reference_chirps/ping_charlie.csv`

每个参考 CSV 只有一列表头 `amplitude`，按采样顺序给出该脉冲的样本值。三条参考脉冲长度相同。

对任一参考脉冲 `template` 和录音 `recording`，定义响应序列：

```text
response[k] = sum(template[j] * recording[k + j] for j in 0..M-1)
```

其中 `M` 是参考脉冲长度，`k` 从 `0` 扫到 `len(recording) - M`。

对每种脉冲分别计算：

- `arrival_sample`：使 `abs(response[k])` 取得最大值的 `k`
- `peak_response`：`abs(response[arrival_sample])`
- `pulse_type`：参考文件名去掉 `.csv` 后的名字

要求：

- 直接使用 WAV 解码后的整数样本值，不要重采样、归一化或裁剪。
- 输出文件必须是 CSV，表头和列顺序固定为 `pulse_type,arrival_sample,peak_response`。
- 输出必须恰好 3 行，每种参考脉冲各 1 行。
- 按 `arrival_sample` 从小到大排序。
- `arrival_sample` 必须是整数；`peak_response` 必须是有限数值。
- 不需要输出额外文件。
