# 任务说明

实验台记录了 6 段独立的复基带采样，每段里都恰好包含 1 个数据包。每个数据包都以前导序列开头，但实际使用的是 3 个候选前导之一，并且包的起始索引未知。请根据给定前导模板，对每个分段做复数滑动相关，找出最匹配的前导 ID 和数据包起始索引，并把结果写到 `/root/frame_sync_results.csv`。

输入文件：

- `/root/data/preamble_catalog.json`
- `/root/data/received_segments.json`

文件中的复数样本统一写成 `[i, q]`，分别表示同相分量和正交分量。把 `[i, q]` 解释为复数 `i + 1j * q`。

`/root/data/preamble_catalog.json` 包含一个 `preambles` 数组；每个元素都有：

- `preamble_id`
- `samples`

`/root/data/received_segments.json` 包含一个 `segments` 数组；每个元素都有：

- `segment_id`
- `samples`

设某个前导模板为 `template`，某个分段为 `segment`，模板长度为 `M`。对每个可能起点 `k`，按下面定义计算响应：

```text
response[k] = sum(conj(template[j]) * segment[k + j] for j in 0..M-1)
score[k] = abs(response[k])
```

其中 `conj(...)` 是复共轭，`k` 从 `0` 扫到 `len(segment) - M`。

对每个分段：

1. 对所有候选前导都计算各自的 `score[k]`。
2. 对每个前导取使 `score[k]` 最大的 `k_peak` 和对应的 `peak_score`。
3. 在所有前导里选择 `peak_score` 最大的那个作为该分段的最终结果。
4. 如果不同前导的 `peak_score` 完全相同，选择字典序更小的 `preamble_id`；如果 `preamble_id` 也相同，再选择更小的 `k_peak`。

把 `/root/frame_sync_results.csv` 写成 CSV，表头和列顺序固定为：

```csv
segment_id,preamble_id,start_index,peak_score
```

要求：

- 输出必须恰好 6 行，每个 `segment_id` 各 1 行。
- `segment_id` 必须来自输入文件，并按字典序升序排列。
- `preamble_id` 必须来自前导目录里的 `preamble_id`。
- `start_index` 必须是整数，表示该分段内数据包前导的起始样本索引。
- `peak_score` 必须是有限数值。
- 不要重采样、滤波、归一化或裁剪输入样本；直接使用文件中的复数样本值。
- 不需要输出中间文件，也不需要生成额外报告。
