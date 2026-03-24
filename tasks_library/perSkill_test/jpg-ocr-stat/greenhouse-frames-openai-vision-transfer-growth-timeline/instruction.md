## 任务说明

`/app/workspace/greenhouse_frames` 下有 7 张同一温室苗床的日序列照片，文件名就是拍摄日期，例如 `2025-04-01.png`。

请按日期顺序读取这些照片，并估计每一天的以下 3 项统计：

- `flowering_plants`: 画面中至少有一朵明显开放黄花的植株数
- `ripe_fruits`: 已成熟、呈明显红色的果实数
- `diseased_leaves`: 具有明显褐色或黑褐色病斑的叶片数

将结果写入 `/app/workspace/growth_timeline.tsv`，并严格使用下面的 TSV 结构：

```tsv
[daily_counts]
date	flowering_plants	ripe_fruits	diseased_leaves
2025-04-01	0	0	0

[peak_dates]
metric	peak_date	peak_value
flowering_plants	2025-04-01	0
ripe_fruits	2025-04-01	0
diseased_leaves	2025-04-01	0
```

要求：

- 文件必须且只能包含上面这两个区块：`[daily_counts]` 和 `[peak_dates]`
- `daily_counts` 区块中的数据行必须按日期升序排列
- `date` 和 `peak_date` 都必须使用 ISO 格式 `YYYY-MM-DD`
- 所有计数都必须是十进制整数
- `peak_value` 是对应指标在所有日期中的最大值
- 如果某个指标的最大值出现在多个日期，`peak_date` 必须填写最早的那个日期
- 不要输出额外区块、额外列、额外说明或额外文件

补充说明：

- 同一株植物即使开了多朵花，在 `flowering_plants` 中也只计 1 株
- 只有明显成熟发红的果实才计入 `ripe_fruits`
- 只有叶片本身出现明显病斑时才计入 `diseased_leaves`，不要把土壤或背景噪点误计为病斑
