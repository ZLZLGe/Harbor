你会在 `/root/data/occultation_session.csv` 得到一段地基小行星掩星观测测光序列。文件包含这些列：

- `frame_id`: 帧编号
- `time_jd`: 儒略日时间戳
- `rel_flux`: 相对光度
- `flux_err`: 每个点的光度误差
- `frame_quality`: 帧质量标记，`0` 表示可用，非零表示坏帧
- `sky_bg`: 天空背景估计
- `seeing_arcsec`: 视宁度

这段序列混有三类常见问题：坏帧、宇宙线造成的尖峰异常、以及云层带来的慢漂移。你的任务不是做掩星建模，而是把这段测光整理成连续可用的观测窗口，并给出每个窗口的归一化亮度统计。

要求：

1. 丢弃所有 `frame_quality != 0` 的观测点。
2. 去掉明显异常尖峰；最终窗口里不要保留明显宇宙线点。
3. 只基于最终保留下来的观测点切分连续窗口：如果相邻两个保留点的时间间隔大于 `90` 秒，就必须开始一个新窗口。
4. 丢弃长度少于 `25` 个点的窗口。
5. 对每个窗口做基线归一化，使 `normalized_flux` 整体围绕 `1` 波动，同时明显压低慢漂移；不要重采样、不要插值、不要跨 gap 合并窗口。
6. 将结果写入 `/root/occultation_windows.json`。

输出 JSON 必须是一个对象，并至少包含：

- `source_file`: 字符串，写成输入文件路径
- `gap_threshold_seconds`: 数值，写成 `90`
- `windows`: 数组

`windows` 中的每个元素都必须至少包含：

- `window_id`: 从 `1` 开始递增的整数
- `start_time`: 该窗口第一条保留观测的 `time_jd`
- `end_time`: 该窗口最后一条保留观测的 `time_jd`
- `n_points`: 该窗口保留点数
- `times`: 该窗口保留观测的时间数组
- `normalized_flux`: 与 `times` 对齐的归一化光度数组
- `mean_flux`: `normalized_flux` 的均值
- `median_flux`: `normalized_flux` 的中位数
- `std_flux`: `normalized_flux` 的总体标准差

额外约束：

1. `windows` 必须按时间顺序输出，窗口内部的 `times` 也必须严格升序。
2. `times` 与 `normalized_flux` 的长度都必须等于 `n_points`。
3. 每个窗口的 `start_time`、`end_time` 必须与对应 `times` 首尾一致。
4. 统计量必须由同一个窗口里的 `normalized_flux` 直接计算得到。
5. 验证会检查每个窗口的 `median_flux` 落在 `0.995` 到 `1.005` 之间，并检查 `11` 点滚动中位数的峰峰值相对原始 `rel_flux` 至少下降 `60%`。
6. 验证还会检查最终所有 `normalized_flux` 都落在 `0.97` 到 `1.02` 之间，用来确认明显尖峰已经被清除。
