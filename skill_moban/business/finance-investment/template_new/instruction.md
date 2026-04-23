你是一名股票研究分析师，需要基于公开财报、公开行情和公开利率数据，对 7 家大型科技公司完成一次可复核的财务质量、市场风险和简化估值排序。

输入数据在：
- `/app/data/sec_companyfacts/`
- `/app/data/prices/`
- `/app/data/fred/`
- `/app/data/reference/company_universe.csv`
- `/app/data/reference/methodology.md`
- `/app/data/reference/source_manifest.json`

其中：
- `sec_companyfacts/` 保存从 SEC EDGAR Company Facts API 抓取并冻结的公司 XBRL JSON。
- `prices/` 保存从公开历史行情端点抓取并冻结的日频 OHLCV CSV。
- `fred/` 保存从 FRED 抓取并冻结的美国 10 年期国债收益率 CSV。
- `company_universe.csv` 给出需要分析的 ticker、CIK、公司名和交易所。
- `methodology.md` 给出指标、估值、打分和建议阈值。

你的任务

1、提取财务报表指标
对 `company_universe.csv` 中的每家公司，从 SEC Company Facts JSON 中提取最近 3 个完整 fiscal year 的年度数据。
至少需要提取：
- revenue
- operating_income
- net_income
- operating_cash_flow
- capital_expenditures
- free_cash_flow
- cash_and_equivalents
- total_debt
- stockholders_equity
- diluted_shares
- diluted_eps

如果同一 fiscal year 存在多个可用 fact，应优先使用：
1. form 为 `10-K` 的记录
2. fiscal period 为 `FY` 的记录
3. filed 日期最新的记录
4. 单位为 USD、shares 或 USD/shares 的记录

2、计算财务质量指标
对每家公司计算：
- revenue_cagr_3y
- operating_margin_latest
- net_margin_latest
- fcf_margin_latest
- return_on_equity_latest
- net_cash_to_revenue_latest
- eps_growth_3y

3、计算市场风险指标
基于 `prices/` 中的日频价格数据，使用最近 252 个交易日计算：
- total_return_252d
- annualized_volatility
- max_drawdown
- beta_to_spy
- sharpe_ratio

风险无风险利率使用 `fred/` 中最近可用的 10-year Treasury rate。SPY 作为市场基准。收益率应使用 `adj_close` 字段。

4、完成简化 DCF 估值
根据 `methodology.md` 的规则，为每家公司计算 base、bull、bear 三种情景的每股 fair value。
DCF 至少需要使用：
- 最近年度 free_cash_flow
- diluted_shares
- revenue_cagr_3y
- cash_and_equivalents
- total_debt
- 10-year Treasury rate
- beta_to_spy
- terminal_growth
- equity_risk_premium

每家公司需要计算：
- base_fair_value
- bull_fair_value
- bear_fair_value
- base_upside_pct
- margin_of_safety

5、生成投资排序和建议
根据 `methodology.md` 的 composite score 规则，对公司排序。每家公司给出一个建议：
- `buy`
- `hold`
- `trim`
- `avoid`

建议必须同时考虑：
- 财务质量
- 市场风险
- DCF upside/downside
- 最大回撤
- 估值安全边际

输出格式：

请在 `/app/output/` 目录下生成以下文件。

1. `/app/output/financial_metrics.csv`

CSV 列必须为：
```text
ticker,company,fiscal_year,revenue,operating_income,net_income,operating_cash_flow,capital_expenditures,free_cash_flow,cash_and_equivalents,total_debt,stockholders_equity,diluted_shares,diluted_eps
```

每家公司应输出最近 3 个完整 fiscal year 的记录。

2. `/app/output/quality_risk_scores.csv`

CSV 列必须为：
```text
ticker,revenue_cagr_3y,operating_margin_latest,net_margin_latest,fcf_margin_latest,return_on_equity_latest,net_cash_to_revenue_latest,eps_growth_3y,total_return_252d,annualized_volatility,max_drawdown,beta_to_spy,sharpe_ratio,composite_score,rank
```

3. `/app/output/valuation.json`

JSON 结构必须为：
```json
{
  "as_of_date": "YYYY-MM-DD",
  "risk_free_rate": 0.0,
  "securities": [
    {
      "ticker": "AAPL",
      "latest_price": 0.0,
      "base_fair_value": 0.0,
      "bull_fair_value": 0.0,
      "bear_fair_value": 0.0,
      "base_upside_pct": 0.0,
      "margin_of_safety": 0.0,
      "recommendation": "buy|hold|trim|avoid"
    }
  ]
}
```

4. `/app/output/investment_ranking.json`

JSON 结构必须为：
```json
{
  "top_pick": "string",
  "avoid_or_trim": ["string"],
  "ranking": [
    {
      "rank": 1,
      "ticker": "string",
      "composite_score": 0.0,
      "recommendation": "buy|hold|trim|avoid",
      "primary_reason": "string"
    }
  ]
}
```

5. `/app/output/research_memo.md`

Markdown 文档，首行必须以 `# ` 开头，并包含以下小节：
```text
## Data Sources
## Financial Quality
## Market Risk
## Valuation
## Ranking And Recommendations
```

说明：
- 所有结果必须由输入数据计算得到，不能手填、随机生成或硬编码答案。
- 不允许联网重新抓取数据；环境中的数据文件已经是公开来源的冻结快照。
- 不允许修改 `/app/data/`、测试文件、依赖配置或环境基线。
- 不允许 hack verifier、读取隐藏答案、伪造输出、删除输入数据或绕过计算流程。
- 输出文件之间必须一致；memo 中的排序、估值和建议必须与 CSV/JSON 一致。
- 数值字段可以保留合理小数位，CSV 和 JSON 中的浮点结果允许存在正常舍入误差。

References for the data files:
[1] SEC EDGAR Company Facts API: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
[2] SEC Company Facts bulk archive: https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip
[3] FRED 10-Year Treasury Constant Maturity Rate: https://fred.stlouisfed.org/series/DGS10
[4] Yahoo Finance chart endpoint: https://query1.finance.yahoo.com/v8/finance/chart/
