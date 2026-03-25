## 任务

俯拍停车场图片位于 `/app/workspace/parking_surveillance`。

每张图片都包含三个固定的水平分区：

- `north`: 最上方停车带
- `center`: 中间停车带
- `south`: 最下方停车带

每个分区固定有 5 个车位。只要一个车位里停着一辆车，就记为 1 个已占用车位；空车位记为 0。图片中的道路、阴影、绿化带都不计入车位数。

读取目录下所有 PNG 图片，生成 `/app/workspace/parking_occupancy.json`。

输出 JSON 的顶层必须且只能包含这些键：

- `captures`
- `peak_timepoints`
- `peak_total_occupied`

规则：

- `captures` 必须是数组，并按 `timepoint` 升序排列。
- `timepoint` 直接使用图片文件名去掉 `.png` 之后的 basename。
- `captures` 中每个元素必须且只能包含这 3 个键：`timepoint`、`zone_counts`、`total_occupied`。
- `zone_counts` 必须且只能包含这 3 个键：`north`、`center`、`south`。
- `zone_counts` 中的每个值都必须是非负整数。
- `total_occupied` 必须等于对应 `zone_counts` 三个分区计数之和。
- `peak_total_occupied` 必须等于所有时间点里最大的 `total_occupied`。
- `peak_timepoints` 必须列出所有达到全局最大占用数的时间点，并按升序排列。
- 不要写入额外字段、额外文件，或改变输出文件路径。

验证会检查 JSON schema、键集合、数值一致性，以及最终内容是否与 oracle 精确一致。
