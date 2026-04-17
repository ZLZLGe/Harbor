# 任务说明（科学图像与视觉模板）

你需要对图像统计特征做标准化处理，输出统一 JSON 报告。

## 输入
- 输入文件：`/app/workspace/input/image_metrics.csv`
- 字段定义：
  - `image_id`：图像编号
  - `width`、`height`：分辨率
  - `bright_pixels`：高亮像素数
  - `total_pixels`：总像素数
  - `edge_score`：边缘强度评分（0~1）

## 输出
- 输出文件：`/app/workspace/output/image_report.json`
- JSON 顶层字段必须包含且仅包含：
  - `image_count`
  - `mean_normalized_brightness`
  - `records`
- `records` 内每条记录必须包含且仅包含：
  - `image_id`
  - `normalized_brightness`
  - `quality_tag`

## 处理规则
1. `normalized_brightness = bright_pixels / total_pixels`，保留 4 位小数。
2. `quality_tag` 规则：
   - `edge_score >= 0.70` -> `sharp`
   - 否则 -> `soft`
3. `records` 按 `image_id` 升序。
4. `mean_normalized_brightness` 为全部 `normalized_brightness` 的平均值，保留 4 位小数。
5. 空值必须用空字符串，不允许 `null`。

## 禁止事项
- 不允许输出额外字段。
- 不允许改变输出层级结构。
- 不允许修改输入文件或使用联网数据。
