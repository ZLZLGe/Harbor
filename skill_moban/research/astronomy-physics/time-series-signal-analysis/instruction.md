# 任务说明（时序信号模板）

你需要对光变曲线样例做确定性统计，并输出结构化 JSON 报告。

## 输入
- 输入文件：`/app/workspace/input/light_curve.csv`
- 字段定义：
  - `time`：时间戳（数值）
  - `flux`：信号强度（数值）

## 输出
- 输出文件：`/app/workspace/output/signal_report.json`
- JSON 顶层字段必须包含且仅包含：
  - `series_id`（字符串，固定为 `template-series-01`）
  - `n_points`（整数）
  - `mean_flux`（浮点）
  - `std_flux`（浮点，使用总体标准差）
  - `min_flux`（浮点）
  - `max_flux`（浮点）
  - `top_peak_times`（长度为 2 的数组，元素为数值）

## 处理规则
1. 所有统计基于全部输入点，不可丢行。
2. `mean_flux` 与 `std_flux` 保留 6 位小数。
3. 峰值时间 `top_peak_times` 按 `flux` 降序选择前 2 个点；若 `flux` 相同，则按 `time` 升序。
4. 输出 JSON 必须可被标准解析器直接读取。

## 禁止事项
- 不允许输出额外字段。
- 不允许修改输入文件。
- 不允许引入随机噪声或外部数据。
