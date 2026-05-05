你正在维护一个湖泊观测站的数据分析流水线。该流水线会从本地观测数据快照中读取水温、气象、水文和周边活动记录，完成质控、时序汇总、趋势检验和驱动因子归因，并把结果交给下游报告系统。目前流水线能够运行，但输出结果存在明显异常：部分站点的长期水温趋势方向与人工抽查不一致，极端值会显著扭曲趋势，贡献率表的总和有时不为 100%，并且下游服务偶尔因为字段缺失拒收结果。

输入数据在 `/root/data/`：
1. `observatory.db`：SQLite 数据库，包含逐小时水温观测、气象观测、河流流量、站点信息和维护事件表。
2. `station_metadata.csv`：站点经纬度、传感器型号、安装深度和启用时间的补充元数据。
3. `event_windows.csv`：已知维护、结冰、传感器漂移和人为活动窗口。
4. `expected_schema.json`：下游报告系统接受的输出字段、类型和允许范围说明。

你的任务：
1. 修复 `/root/workspace/` 中现有分析流水线，使它继续通过原有 CLI 入口读取上述真实数据链路并生成结果；不要改成只读静态文件、只写固定答案或绕过数据库查询。
2. 正确识别并处理输入数据结构：按站点和时间对齐 SQLite 表与 CSV 元数据，保留真实站点维度，处理重复观测、缺失值、单位换算、维护窗口、传感器漂移标记和质控标志。
3. 生成逐站点水温趋势结果：仅使用通过质控的观测值，先聚合为日尺度站点序列，再计算长期水温趋势、显著性和数据质量指标；趋势估计应对少量极端值具有鲁棒性。
4. 生成驱动因子归因结果：把候选解释变量归入 `Heat`、`Flow`、`Wind`、`Human` 四类，使用同一套质控后的日尺度数据估计各类对水温变化的相对贡献，并保证贡献率可解释、可复核且总和为 100%。
5. 生成机器可读的运行摘要，记录输入规模、质控过滤数量、分析时间范围、主导因子、模型质量指标和必要警告，供下游报告系统校验。

输出格式：
所有输出必须写入 `/root/output/`，文件名和字段必须如下。

`station_trends.csv`
```csv
station_id,station_name,start_date,end_date,n_days,valid_observations,missing_rate,outlier_rate,temp_slope_c_per_year,p_value,trend_method
```
- `station_id`、`station_name` 必须来自输入数据，不得自行改名或合并站点。
- `start_date`、`end_date` 使用 `YYYY-MM-DD`。
- `n_days`、`valid_observations` 为整数。
- `missing_rate`、`outlier_rate`、`temp_slope_c_per_year`、`p_value` 保留 6 位小数。
- `trend_method` 写明实际使用的鲁棒趋势方法名称。

`driver_attribution.csv`
```csv
category,contribution_pct,signed_effect,rank,n_features
```
- `category` 只能是 `Heat`、`Flow`、`Wind`、`Human`。
- 必须输出四行，每个类别一行。
- `contribution_pct` 为非负百分比，四类合计必须为 `100.000000`（允许最后一类因四舍五入补差）。
- `signed_effect` 保留 6 位小数，用于表示该类别对水温变化方向的净效应。
- `rank` 从 1 开始，1 表示贡献率最高；并列时按 `Heat`、`Flow`、`Wind`、`Human` 的顺序稳定排序。
- `n_features` 为该类别实际参与模型的特征数量。


`analysis_workflow_audit.json`
```json
{
  "sql_queries": [],
  "pandas_operations": [],
  "statistical_checks": [],
  "performance_considerations": [],
  "example_results": [],
  "skill_output_format": {
    "clear_comments_or_notes": [],
    "example_results": [],
    "performance_considerations": [],
    "interpretation_of_findings": []
  },
  "interpretation": {
    "dominant_category": "Heat",
    "warming_station_count": 0,
    "key_findings": []
  }
}
```
- `sql_queries` 至少列出 3 个实际使用的 SQLite 查询或查询目的，并说明涉及的表和 join/filter 口径。
- `pandas_operations` 至少列出 5 个实际执行的数据处理步骤，包括去重、合并、过滤、聚合和缺失/单位处理。
- `statistical_checks` 至少列出 3 个统计检查，包括趋势方法、显著性检验和归因模型。
- `performance_considerations` 至少列出 2 条性能或可复现性考虑，例如避免重复读库、稳定排序、向量化、确定性输出或按站点分组计算。
- `example_results` 至少列出 3 条从本次输出中抽取的示例结果，例如某个站点趋势、主导因子和贡献率总和。
- `skill_output_format` 用来记录分析交付是否包含清晰说明、示例结果、性能考虑和发现解释；四个子字段都必须存在且不能是空列表。
- `interpretation` 必须和 CSV/summary 输出一致，用简短机器可读字段解释主导因子、显著升温站点数量和关键发现。

`run_summary.json`
```json
{
  "dataset": {
    "stations": 0,
    "raw_observations": 0,
    "daily_records": 0,
    "analysis_start": "YYYY-MM-DD",
    "analysis_end": "YYYY-MM-DD"
  },
  "quality_control": {
    "dropped_duplicate_rows": 0,
    "dropped_qc_rows": 0,
    "dropped_event_window_rows": 0,
    "imputed_daily_values": 0
  },
  "trend": {
    "method": "...",
    "stations_with_significant_warming": 0,
    "median_slope_c_per_year": 0.0
  },
  "attribution": {
    "method": "...",
    "dominant_category": "Heat",
    "model_r2": 0.0,
    "contribution_sum": 100.0
  },
  "warnings": []
}
```
- JSON 字段必须存在；允许添加额外说明字段，但不能删除或改名上述字段。
- 数值字段必须使用 JSON number，不要用字符串包裹。

说明：
- 可以修改 `/root/workspace/` 中的流水线代码、配置和辅助脚本；不要修改 `/root/data/` 中的输入数据。
- 可以使用 `pandas`、`numpy`、`scipy`、`statsmodels`、`scikit-learn`、SQLite 查询或项目中已有依赖；不要引入需要外部账号、云权限或交互式登录的服务。
- 禁止用硬编码答案、删除功能、跳过质控、伪造空结果、替换为固定样例数据或让下游校验逻辑失效来规避问题。
- 如果发现某个站点或日期无法用于分析，应在质控统计或 `warnings` 中说明原因，而不是静默丢弃全部数据。
- 输出结果应具有确定性：相同输入和相同代码多次运行应产生一致文件内容。
