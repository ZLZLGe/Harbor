# 任务说明（数据转换模板）

你需要读取输入数据并生成标准化汇总表，重点演示科学数据的抽取、转换、计算与稳定输出。

## 输入
- 输入文件：`/app/workspace/input/observations.csv`
- 字段定义：
  - `object_id`：目标编号（字符串）
  - `flux_jy`：观测流量（Jy，可能为空）
  - `distance_pc`：距离（pc，可能为空）
  - `quality_flag`：质量标记（`ok` / `review` / `drop`）

## 输出
- 输出文件：`/app/workspace/output/summary.csv`
- 必须包含且仅包含以下字段（顺序固定）：
  - `object_id`
  - `flux_mjy`
  - `luminosity_proxy`
  - `quality_flag`

## 处理规则
1. 仅保留 `quality_flag != "drop"` 的记录。
2. `flux_mjy = flux_jy * 1000`，保留 3 位小数；当 `flux_jy` 为空时输出空字符串。
3. `luminosity_proxy = flux_jy * distance_pc^2`，保留 4 位小数；任一输入为空时输出空字符串。
4. 输出按 `object_id` 升序排序。
5. 空值必须输出为空字符串，不能输出 `null`、`None`、`nan`。

## 禁止事项
- 不允许修改输入文件。
- 不允许写出额外结果文件替代主输出。
- 不允许依赖随机行为或联网数据。
