# 任务说明

你拿到了一份已经做过基础调理和白化的双探测器应变数据，以及一个小型并合模板库。请在 Hanford (`H1`) 和 Livingston (`L1`) 两路数据上逐个扫描模板，找出网络分数最高的候选事件，并把结果写到 `/root/coincident_trigger.json`。

输入文件是 `/root/data/coincident_inputs.npz`，其中包含以下键：

- `sample_rate_hz`：采样率，单位 Hz。
- `gps_start`：两路数据共同的起始 GPS 时间。
- `h1_strain`：Hanford 应变数组。
- `l1_strain`：Livingston 应变数组。
- `template_ids`：模板 ID 数组。
- `templates`：模板矩阵；第 `i` 行与 `template_ids[i]` 对应。

数据已经白化，可以直接对每个模板做滑动内积。对任一探测器、任一模板，按下面的定义计算一条触发时间序列：

```text
snr[k] = sum(template[j] * strain[k + j] for j in 0..M-1)
```

其中 `M` 是模板长度，`k` 从 `0` 扫到 `len(strain) - M`。对每个探测器取 `abs(snr[k])` 的最大值作为该模板在该探测器上的峰值 SNR，并记录对应的峰值样本位置 `k_peak`。

时间定义如下：

- 探测器峰值时间 = `gps_start + (k_peak + M / 2) / sample_rate_hz`
- 事件时间 = `(h1_peak_time + l1_peak_time) / 2`

每个模板的网络分数定义为：

```text
network_snr = sqrt(h1_peak_snr^2 + l1_peak_snr^2)
```

选择 `network_snr` 最大的模板作为最终答案；如果出现完全相同的网络分数，选择字典序更小的 `template_id`。

把 `/root/coincident_trigger.json` 写成一个 JSON 对象，至少包含以下字段：

```json
{
  "template_id": "模板 ID",
  "event_time": 0.0,
  "h1_peak_snr": 0.0,
  "l1_peak_snr": 0.0
}
```

要求：

- `template_id` 必须来自输入文件里的 `template_ids`。
- `event_time`、`h1_peak_snr`、`l1_peak_snr` 都必须是 JSON 数值。
- 不需要输出中间结果，也不需要生成额外文件。
