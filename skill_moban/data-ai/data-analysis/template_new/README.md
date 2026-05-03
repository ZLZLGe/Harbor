# Data Analysis Template

这是面向 `data-analysis` 类 skill 的模板。它综合参考 SkillsMP data-analysis 类热门 skill 的共性能力：读取本地数据快照、梳理 SQL 提取口径、完成 pandas 聚合与统计比较，并把结论沉淀为可复跑交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：data-analysis 类热门 skill 的共同价值，在于帮助 Agent 先识别数据结构、口径和异常，再把 SQL 提取、pandas 整理、统计比较和结论解释连成一条完整路径。高质量模板应让 skill 在“如何从源数据稳定走到结论”上提供帮助，避免任务退化成静态答案生成。
* **Task 目标形态**：这类任务适合设计成多来源分析交付题，例如本地数据库、维表、天气或活动因素一起进入判断，最终产出推荐名单、明细表、质量检查和简洁说明文档。目标应强调可运行、可追溯和可重复执行，不应退化成只改格式或只补文案的题。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿数据链路完成清洗、聚合、统计和结果回写，并检查多份交付物之间的一致性。对于绑定了工作流型 skill 的任务，还应验证 solver 是否保留了可复用的 SQL 提取逻辑与解释性说明。

## 第二部分：示例任务

### 📌 任务元数据
- 任务 ID：`data-analysis__airport-partner-zone-opportunity`
- 类别：`data-analysis`
- 难度：`hard`
- 绑定 Skill：`data-analyst`
- 输入数据参考来源：
  - `environment/data/trips/airport_partner_ops.db`：任务内 SQLite staging 数据；设计形态参考 NYC TLC Yellow Taxi Trip Records 与 zone lookup  
    【https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet】
    【https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-02.parquet】
    【https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv】
  - `environment/data/reference/trip_record_user_guide.pdf`：任务内字段说明参考；数据直接来源于 NYC TLC  
    【https://www.nyc.gov/assets/tlc/downloads/pdf/trip_record_user_guide.pdf】
  - `environment/data/reference/data_dictionary_trip_records_yellow.pdf`：任务内 Yellow Taxi 字段字典；数据直接来源于 NYC TLC  
    【https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf】
  - `environment/data/weather/airport_daily_weather.json`：任务内机场日级天气数据；数据直接来源于 NOAA Daily Summaries API  
    【https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00094789,USW00014732,USW00014734&startDate=2023-01-01&endDate=2023-02-07&dataTypes=AWND,PRCP,SNOW,SNWD,TMAX,TMIN&includeAttributes=false&includeStationName=true&includeStationLocation=1&units=metric&format=json】

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：Oracle 从任务内 SQLite staging DB、机场天气 JSON 和 planning contract 重新计算工作日 airport partner-zone 明细、天气敏感性和支持名单，再生成说明文档与 SQL query pack；它不依赖隐藏答案表，直接从输入重算。
- Verifier 策略：

主测试
| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 运行入口 | 校验 `run_airport_partner_analysis.py` 能基于当前输入生成全部交付物 | 从统一入口组织分析链路 |
| SQLite 提取链路 | 校验 solver 查询 SQLite、读取 planning contract，并保留月表差异识别 | SQL 提取、合同口径阅读 |
| period 汇总 | 校验 `airport_partner_zone_period_summary.csv` 的 row scope、关键分组键和核心指标容差 | pandas 聚合、候选区域筛选、period-level 追溯 |
| 天气敏感性 | 校验 `airport_weather_sensitivity.tsv` 的 bucket 结构、方向判断和关键指标容差 | 统计比较、效果解释 |
| 支持名单 | 精确比对 `airport_partner_zone_rankings.tsv` 的推荐对象与业务动作 | 排序规则、资格门槛和建议回写 |
| 说明与 SQL pack | 校验 markdown 与 `query_pack.sql` 是否和核心结果一致 | 结果解释与可复用查询沉淀 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 合同变更重跑 | 改动 `analysis_contract.json` 后 rerun，支持名单必须随之变化 |
| 静态答案拦截 | 禁止硬编码区域答案、绕过 SQLite、依赖外部账号或把结论直接写死在输出中 |

### ⚡ Skill 相关性评估

结论：中等偏强相关。这个任务里，Skill 的核心价值仍然落在 SQLite 提取、schema drift 识别、pandas 整理、统计比较和 query pack 留存的联动上；不过从对照结果看，skill 更稳定地帮助代理走到完整分析链路，但并不能把所有 trial 都收敛到同一业务结论。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除 build cancelled 类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33%` | 3 组有效对照里，without skill 没有一次完整通过；with skill 有 1 次完整通过，说明 skill 对收敛有帮助，但稳定性仍需继续提升 |
| Agent 执行耗时 | `629.5s` | `611.1s` | With skill 的平均 Agent 耗时降低约 `2.9%` |
| Tokens | `733.3k` | `696.7k` | With skill 的平均 token 开销降低约 `5.0%` |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── skills/
│   └── workspace/
├── tests/
│   ├── reference_metrics.py
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    ├── fixed/
    │   └── run_airport_partner_analysis.py
    └── solve.sh
```
