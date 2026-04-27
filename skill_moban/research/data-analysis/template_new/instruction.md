你正在为一家区域连锁生鲜零售商完成一份“促销活动真实收益与库存风险复盘”。当前分析包把门店时区、退单、重复交易、缺货暴露和天气异常混在一起，导致促销 ROI、品类 uplift 和门店风险排序互相矛盾，业务复核无法通过。

输入数据在：
- `/root/environment/data/pos/`：门店 POS 交易事件
- `/root/environment/data/catalog/`：商品、品类、促销活动、门店主数据和分析合同
- `/root/environment/data/inventory/`：门店商品级库存快照
- `/root/environment/data/external/`：天气、节假日和区域客流指数数据
- `/root/environment/pipeline/`：当前可运行但分析口径错误的分析入口与脚本
- `/services/promo-enrichment/server.py`：同容器内的本地下游促销注释服务启动入口，只允许调用，不允许修改

当前症状：
- 当前 ROI 排名把部分高退单、高折扣或跨日交易的门店误判成高收益门店
- 若按 UTC 日期聚合，若干门店的促销前后窗口会错位，导致 uplift 方向反转
- 当前缺货风险表只统计了库存事件次数，没有按真实缺货暴露时长和促销窗口重叠计算
- 品类摘要中出现了未进入最终可报告结果的品类，且图表数据、CSV 明细和 JSON 报告中的数值不一致
- 下游促销注释摘要引用了错误的门店和品类组合，无法支撑最终业务结论

你的任务

1、基于提供的 POS、商品、库存、天气、节假日和客流数据，重建促销活动复盘分析链路。

2、确保最终结果反映的是促销活动带来的真实增量表现，而不是退单、重复交易、时区错位、天气异常、节假日或缺货暴露造成的混杂信号。

3、修复并运行正式分析入口，使以下命令能够成功生成最终交付物：

```bash
python /root/environment/pipeline/run_analysis.py --output /root/answer
```

4、分析必须至少覆盖以下业务指标：
- `net_revenue`：扣除退单、取消订单和商品级折扣后的净销售额
- `net_units`：扣除退单和取消订单后的净销量
- `gross_margin`：基于商品成本计算的毛利额
- `promo_uplift_pct`：促销窗口相对可比基线窗口的净销售额提升比例
- `incremental_margin`：促销窗口相对校正后基线窗口的增量毛利
- `stockout_exposure_hours`：促销窗口内商品处于缺货状态的真实暴露小时数
- `adjusted_roi`：考虑折扣、退单、促销费用、缺货暴露和混杂因素后的促销 ROI

5、促销前后窗口必须按门店本地业务日期计算，而不是按 UTC 日期计算。不同门店可以属于不同 IANA 时区。

6、POS 事件必须按 `order_id` 去重。若同一订单存在多条事件，使用 `event_at_utc` 最大的记录；若仍并列，使用 `ingested_at_utc` 最大的记录；若仍并列，使用 `event_id` 最大的记录。最终状态为 `completed` 的订单才可以贡献收入、销量和毛利。

7、校正后基线必须使用 `/root/environment/data/catalog/analysis_contract.json` 中的参数，并控制以下因素：
- 门店差异
- 品类差异
- 本地业务日期和星期结构
- 节假日效应
- 天气异常
- 区域客流指数
- 促销窗口内缺货暴露

8、缺货暴露必须从库存快照的状态区间计算。`on_hand <= 0` 的区间视为缺货，区间起止必须裁剪到对应促销窗口内，不能只统计缺货事件数量。

9、最终结果必须同时保留未校正基线口径和校正后口径，明确区分：
- 稳定有效的促销信号
- 只有在校正混杂因素后才恢复的促销信号
- 基线口径中会被误报的促销信号
- 因缺货暴露过高而不适合报告为有效 uplift 的促销信号

10、继续通过本地 `promo-enrichment` 服务完成促销注释汇总。最终报告中的促销解释、品类标签和门店区域信息必须来自真实服务响应，不能伪造或静态替换。

输出格式：

- `/root/answer/promo_performance.csv`
  - 必须包含列：`store_id`, `promo_id`, `category_id`, `business_start_date`, `business_end_date`, `net_revenue`, `net_units`, `gross_margin`, `baseline_net_revenue`, `promo_uplift_pct`, `incremental_margin`, `stockout_exposure_hours`, `adjusted_roi`, `reportable`

- `/root/answer/category_uplift.tsv`
  - 必须包含每个促销品类的基线口径与校正后口径结果
  - 至少包含列：`category_id`, `category_name`, `baseline_uplift_pct`, `adjusted_uplift_pct`, `adjusted_pvalue`, `adjusted_qvalue`, `direction`, `diagnostic_status`

- `/root/answer/store_risk_audit.tsv`
  - 必须覆盖参与促销的全部门店
  - 必须包含退单率、重复交易率、缺货暴露、天气异常、客流异常和最终风险等级
  - 风险等级必须与最终 ROI 和可报告状态一致

- `/root/answer/analysis_diagnostics.tsv`
  - 必须覆盖全部参与促销的 `(store_id, promo_id, category_id)` 组合
  - 必须同时包含未校正基线模型和校正后模型的核心统计结果
  - 必须包含最终诊断状态和是否可报告标记

- `/root/answer/promo_summary.json`
  - 顶层必须包含键：`analysis_window`, `n_promotions`, `n_store_promo_category_rows`, `n_reportable_rows`, `top_promotions`, `category_summary`, `risk_summary`, `model_summary`, `enrichment_summary`, `notes`
  - `model_summary` 中必须明确说明未校正基线口径和校正后口径分别使用的特征或公式
  - `top_promotions` 中的门店、促销和品类组合必须能在 CSV/TSV 明细中追溯

- `/root/answer/figures/promo_roi_by_category.csv`
  - 必须是用于绘图的长表数据，而不是图片
  - 必须与 `category_uplift.tsv` 和 `promo_summary.json` 中的品类 ROI / uplift 结论一致

- `/root/answer/figures/store_risk_matrix.csv`
  - 必须是用于绘图的长表数据
  - 必须与 `store_risk_audit.tsv` 中的门店风险等级和关键风险因子一致

说明：

- 可以使用 SQL、pandas、duckdb、statsmodels 或其他已安装的数据分析工具，但最终交付物必须由正式分析入口生成。
- 不要替换真实链路，不要把 POS 处理、库存暴露计算、混杂校正、促销注释服务调用或报告汇总改成静态假数据、手写结果、本地伪造响应或直接复制错误输出后微调。
- 不要通过删功能规避问题，例如跳过退单处理、跳过重复交易去重、跳过本地日期转换、跳过缺货暴露计算、跳过混杂校正、停用多重检验校正，或把所有促销都标成可报告或不可报告。
- 不要修改输入数据、隐藏下游服务、测试文件、环境基线或依赖配置。
- 不要把最终输出绑定到样例数据中的固定行顺序；评分以正式交付物的行为结果、统计一致性和真实分析链路为准。
- 可以增加日志、辅助脚本或局部重构；若编写临时分析文件，最终仍需把正确结果写回 `/root/answer` 下的正式交付物。
