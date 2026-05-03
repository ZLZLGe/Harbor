你要为机场运营规划组准备一份工作日 airport partner-zone 机会分析包。团队已经把多批次行程 staging DB、机场天气快照、planning contract 和字段参考放进本地环境，但还没有正式交付文件。

输入数据在：
- `/root/data/trips/airport_partner_ops.db`：SQLite 数据库，包含 `dispatch_batch_a`、`dispatch_batch_b`、`dispatch_batch_c`、`dispatch_batch_d` 和 `zone_lookup`
- `/root/data/weather/airport_daily_weather.json`：JFK、LGA、EWR 的日级天气快照
- `/root/data/planning/analysis_contract.json`：分析窗口、机场映射、时段、有效 trip 规则、天气分层、排序规则和输出契约
- `/root/data/reference/`：zone lookup 参考表和字段说明文档
- `/root/workspace/`：正式分析入口及本地工作区

你的任务

1、基于 staging DB、weather 和 planning contract，把多批次行程数据统一成可分析口径，完成工作日 airport partner-zone 机会分析，并生成最终交付物。

2、交付 morning departures 和 evening arrivals 两类支持名单，并让结论能够追溯到 period-level 汇总结果和可复用查询口径。

输出：

- `/root/output/analysis_brief.md`
  - 必须包含标题：`Scope`、`Morning departures`、`Evening arrivals`、`Weather notes`、`Method notes`

- `/root/output/source_inventory.tsv`
  - 必须使用这些列，顺序保持一致：`source_name`, `path`, `grain`, `date_range`, `key_fields`, `note`
  - 只列 4 条输入包：staging DB、airport weather、planning contract、reference docs

- `/root/output/quality_checks.tsv`
  - 必须使用这些列，顺序保持一致：`check_id`, `dataset`, `status`, `metric_name`, `metric_value`, `note`

- `/root/output/airport_partner_zone_period_summary.csv`
  - 必须使用这些列，顺序保持一致：`period`, `airport_code`, `partner_zone_id`, `partner_zone_name`, `borough`, `active_service_days`, `total_airport_trips`, `total_partner_zone_trips`, `avg_airport_trip_share`, `median_trip_duration_min`, `median_total_amount`, `weather_resilience_score`, `opportunity_score`

- `/root/output/airport_weather_sensitivity.tsv`
  - 必须使用这些列，顺序保持一致：`period`, `airport_code`, `weather_bucket`, `avg_airport_trip_count`, `avg_airport_trip_share`, `avg_median_trip_duration_min`, `n_zone_days`, `vs_dry_u_test_pvalue`, `effect_direction`

- `/root/output/airport_partner_zone_rankings.tsv`
  - 必须使用这些列，顺序保持一致：`period`, `airport_code`, `recommendation_type`, `rank`, `zone_id`, `zone_name`, `borough`, `active_service_days`, `avg_airport_trip_count`, `avg_airport_trip_share`, `weather_resilience_score`, `opportunity_score`, `recommended_action`, `reason_code`

- `/root/output/query_pack.sql`
  - 必须是合法的 UTF-8 SQL 文本，保留可复用的关键提取查询
  - 用 `-- Query 1:` 这样的编号注释组织关键查询

说明：

- 工作日范围、机场映射、时段窗口、候选区域、有效 trip 规则、天气分层、资格门槛、排序规则、推荐名额和输出字段，必须遵循 `/root/data/planning/analysis_contract.json`。
- 4 个 staging batch 承载的是同一类业务事实，但字段命名并不一致；最终结果要先完成统一口径，再进入聚合、天气比较和推荐排序。
- 时段筛选统一使用 `pickup_timestamp` 的整点小时；`morning_departures` 取 `06:00:00` 到 `10:59:59`，`evening_arrivals` 取 `17:00:00` 到 `22:59:59`。
- `airport_partner_zone_period_summary.csv` 只保留在分析窗口内实际出现过 airport-linked trip 的 `period + airport_code + partner_zone_id` 组合。
- `total_partner_zone_trips` 表示同一 `period + partner_zone_id + service_date` 在对应时段内全部过滤后 trip 的日级总量，再按输出粒度汇总；这个日级分母面板要覆盖该 `period + partner_zone_id` 的全部观测服务日，不要只保留某个机场出现过 airport-linked trip 的活跃日。`total_airport_trips` 仅统计其中满足机场映射方向的 trip。
- `active_service_days` 统计该 `period + airport_code + partner_zone_id` 组合下，至少出现过 1 笔 airport-linked trip 的服务日数量。
- `avg_airport_trip_share` 需要先按服务日计算 `airport_trip_count / partner_trip_count`，再在该 partner zone 的全部观测服务日上取平均；若某个服务日该机场没有 airport-linked trip，这一天的 `airport_trip_count` 视为 `0`。
- `opportunity_score` 的计算和排序口径要直接读取 contract 里的 `ranking_score` 定义：先在同一 `period + airport_code` 内完成 count/share/resilience 的归一化，再按其中给出的权重和 tie-break 顺序产出支持名单。
- `airport_weather_sensitivity.tsv` 的 `effect_direction` 取值要遵循 contract 中 `weather_effect_output.effect_direction_values`；天气比较也要基于上面这套完整的 `period + partner_zone_id + service_date` 面板。
- `quality_checks.tsv` 中建议覆盖的检查项和推荐的数据集命名，也已经写在 contract 的 `quality_check_contract` 里。
- `analysis_brief.md` 中的 morning departures 和 evening arrivals 两节，需要点名写出最终入选支持名单中的区域名称。
- 以下命令必须可以成功生成结果：

```bash
python /root/workspace/run_airport_partner_analysis.py --data /root/data --output /root/output
```

- 不要修改输入数据、测试文件、环境基线或依赖配置。
- 不要手写最终答案文件，不要把结论直接写死在输出中。
- 不要跳过 staging batch 统一、候选区域筛选、机场映射、天气分层、资格门槛或两类支持名单生成。
- 可以补充辅助脚本，但最终仍需由正式入口把结果写入 `/root/output`。
