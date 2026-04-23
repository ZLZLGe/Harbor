from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DATA_ROOT = Path(os.environ.get("FINANCE_DATA_ROOT", "/app/data"))
OUTPUT_ROOT = Path(os.environ.get("FINANCE_OUTPUT_ROOT", "/app/output"))

SEC_ROOT = DATA_ROOT / "sec_companyfacts"
PRICE_ROOT = DATA_ROOT / "prices"
FRED_PATH = DATA_ROOT / "fred" / "DGS10.csv"
UNIVERSE_PATH = DATA_ROOT / "reference" / "company_universe.csv"

USD = "USD"
SHARES = "shares"
EPS_UNIT = "USD/shares"

CONCEPTS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
    ],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "capital_expenditures": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndCashEquivalentsAndShortTermInvestments",
    ],
    "current_debt": [
        "LongTermDebtAndFinanceLeaseObligationsCurrent",
        "LongTermDebtCurrent",
        "ShortTermBorrowings",
    ],
    "noncurrent_debt": [
        "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
        "LongTermDebtNoncurrent",
    ],
    "total_debt": ["LongTermDebtAndFinanceLeaseObligations", "LongTermDebt"],
    "stockholders_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "diluted_shares": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "CommonStockSharesOutstanding",
    ],
    "diluted_eps": ["EarningsPerShareDiluted"],
}


def finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def round_float(value: float, digits: int = 6) -> float:
    if not finite(value):
        return 0.0
    if abs(value) < 0.5 * 10 ** (-digits):
        return 0.0
    return round(float(value), digits)


def read_universe() -> list[dict[str, str]]:
    with UNIVERSE_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def company_facts(ticker: str) -> dict[str, Any]:
    return json.loads((SEC_ROOT / f"{ticker}.json").read_text(encoding="utf-8"))


def fact_candidates(data: dict[str, Any], concepts: list[str], unit: str) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    us_gaap = data.get("facts", {}).get("us-gaap", {})
    for concept in concepts:
        facts = us_gaap.get(concept, {}).get("units", {}).get(unit, [])
        for fact in facts:
            if fact.get("form") != "10-K" or fact.get("fp") != "FY":
                continue
            year = fact.get("fy")
            if not isinstance(year, int) or not finite(fact.get("val")):
                continue
            result.setdefault(year, []).append(fact)
    return result


def select_value(data: dict[str, Any], concepts: list[str], unit: str, fiscal_year: int) -> float | None:
    for concept in concepts:
        by_year = fact_candidates(data, [concept], unit)
        facts = by_year.get(fiscal_year, [])
        if not facts:
            continue
        facts = sorted(
            facts,
            key=lambda item: (
                str(item.get("filed", "")),
                str(item.get("end", "")),
                str(item.get("accn", "")),
            ),
            reverse=True,
        )
        return float(facts[0]["val"])
    return None


def available_years(data: dict[str, Any]) -> list[int]:
    years: set[int] = set()
    for name in [
        "revenue",
        "operating_income",
        "net_income",
        "operating_cash_flow",
        "capital_expenditures",
        "stockholders_equity",
        "diluted_shares",
        "diluted_eps",
    ]:
        unit = EPS_UNIT if name == "diluted_eps" else SHARES if name == "diluted_shares" else USD
        years.update(fact_candidates(data, CONCEPTS[name], unit))
    return sorted(years)


def total_debt(data: dict[str, Any], fiscal_year: int) -> float:
    current = select_value(data, CONCEPTS["current_debt"], USD, fiscal_year)
    noncurrent = select_value(data, CONCEPTS["noncurrent_debt"], USD, fiscal_year)
    if current is not None or noncurrent is not None:
        return float(current or 0.0) + float(noncurrent or 0.0)
    fallback = select_value(data, CONCEPTS["total_debt"], USD, fiscal_year)
    return float(fallback or 0.0)


def financial_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for company in read_universe():
        ticker = company["ticker"]
        data = company_facts(ticker)
        complete: list[tuple[int, dict[str, float]]] = []
        for year in available_years(data):
            values = {
                "revenue": select_value(data, CONCEPTS["revenue"], USD, year),
                "operating_income": select_value(data, CONCEPTS["operating_income"], USD, year),
                "net_income": select_value(data, CONCEPTS["net_income"], USD, year),
                "operating_cash_flow": select_value(data, CONCEPTS["operating_cash_flow"], USD, year),
                "capital_expenditures": select_value(data, CONCEPTS["capital_expenditures"], USD, year),
                "cash_and_equivalents": select_value(data, CONCEPTS["cash_and_equivalents"], USD, year),
                "stockholders_equity": select_value(data, CONCEPTS["stockholders_equity"], USD, year),
                "diluted_shares": select_value(data, CONCEPTS["diluted_shares"], SHARES, year),
                "diluted_eps": select_value(data, CONCEPTS["diluted_eps"], EPS_UNIT, year),
            }
            if any(value is None for value in values.values()):
                continue
            capex = abs(float(values["capital_expenditures"]))
            ocf = float(values["operating_cash_flow"])
            complete.append(
                (
                    year,
                    {
                        "revenue": float(values["revenue"]),
                        "operating_income": float(values["operating_income"]),
                        "net_income": float(values["net_income"]),
                        "operating_cash_flow": ocf,
                        "capital_expenditures": capex,
                        "free_cash_flow": ocf - capex,
                        "cash_and_equivalents": float(values["cash_and_equivalents"]),
                        "total_debt": total_debt(data, year),
                        "stockholders_equity": float(values["stockholders_equity"]),
                        "diluted_shares": float(values["diluted_shares"]),
                        "diluted_eps": float(values["diluted_eps"]),
                    },
                )
            )
        latest_three = sorted(complete, key=lambda item: item[0])[-3:]
        for year, values in latest_three:
            row: dict[str, Any] = {
                "ticker": ticker,
                "company": company["company"],
                "fiscal_year": year,
            }
            row.update(values)
            rows.append(row)
    return sorted(rows, key=lambda row: (row["ticker"], int(row["fiscal_year"])))


def read_prices(ticker: str) -> pd.DataFrame:
    df = pd.read_csv(PRICE_ROOT / f"{ticker}.csv", parse_dates=["date"])
    df = df.sort_values("date")
    df = df[df["adj_close"].notna()].copy()
    return df


def risk_free_rate(as_of_date: pd.Timestamp) -> float:
    df = pd.read_csv(FRED_PATH, parse_dates=["observation_date"])
    df = df[df["DGS10"] != "."].copy()
    df["DGS10"] = df["DGS10"].astype(float)
    df = df[df["observation_date"] <= as_of_date]
    if df.empty:
        raise ValueError("No DGS10 observation on or before as_of_date")
    return float(df.iloc[-1]["DGS10"]) / 100.0


def latest_common_price_date(tickers: list[str]) -> pd.Timestamp:
    latest = [read_prices(ticker)["date"].max() for ticker in tickers + ["SPY"]]
    return min(latest)


def price_window(ticker: str, as_of_date: pd.Timestamp) -> pd.DataFrame:
    df = read_prices(ticker)
    df = df[df["date"] <= as_of_date].tail(253).copy()
    if len(df) < 253:
        raise ValueError(f"Not enough prices for {ticker}")
    df["daily_return"] = df["adj_close"].pct_change()
    return df


def max_drawdown(prices: pd.Series) -> float:
    running_max = prices.cummax()
    drawdown = prices / running_max - 1.0
    return float(drawdown.min())


def risk_metrics(tickers: list[str], as_of_date: pd.Timestamp, rf: float) -> dict[str, dict[str, float]]:
    spy = price_window("SPY", as_of_date)[["date", "daily_return"]].dropna()
    results: dict[str, dict[str, float]] = {}
    for ticker in tickers:
        window = price_window(ticker, as_of_date)
        returns = window["daily_return"].dropna()
        annual_vol = float(returns.std(ddof=1) * math.sqrt(252))
        aligned = (
            window[["date", "daily_return"]]
            .dropna()
            .merge(spy, on="date", suffixes=("_asset", "_spy"))
        )
        beta = float(np.cov(aligned["daily_return_asset"], aligned["daily_return_spy"], ddof=1)[0, 1] / np.var(aligned["daily_return_spy"], ddof=1))
        sharpe = float(((returns - rf / 252.0).mean() * 252.0) / annual_vol)
        results[ticker] = {
            "latest_price": float(window.iloc[-1]["adj_close"]),
            "total_return_252d": float(window.iloc[-1]["adj_close"] / window.iloc[0]["adj_close"] - 1.0),
            "annualized_volatility": annual_vol,
            "max_drawdown": max_drawdown(window["adj_close"]),
            "beta_to_spy": beta,
            "sharpe_ratio": sharpe,
        }
    return results


def cagr(latest: float, earliest: float, years: int) -> float:
    if earliest <= 0 or latest <= 0 or years <= 0:
        return 0.0
    return float((latest / earliest) ** (1.0 / years) - 1.0)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def zscores(values: list[float]) -> list[float]:
    arr = np.array(values, dtype=float)
    std = float(arr.std(ddof=0))
    if std == 0.0:
        return [0.0 for _ in values]
    mean = float(arr.mean())
    return [float((value - mean) / std) for value in values]


def build_bundle() -> dict[str, Any]:
    companies = read_universe()
    tickers = [row["ticker"] for row in companies]
    company_names = {row["ticker"]: row["company"] for row in companies}
    fin_rows = financial_rows()
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for row in fin_rows:
        by_ticker.setdefault(row["ticker"], []).append(row)

    as_of_date = latest_common_price_date(tickers)
    rf = risk_free_rate(as_of_date)
    risks = risk_metrics(tickers, as_of_date, rf)

    score_base: dict[str, dict[str, float]] = {}
    valuations: dict[str, dict[str, float | str]] = {}
    for ticker in tickers:
        rows = sorted(by_ticker[ticker], key=lambda row: int(row["fiscal_year"]))
        earliest, latest = rows[0], rows[-1]
        year_gap = int(latest["fiscal_year"]) - int(earliest["fiscal_year"])
        revenue_cagr = cagr(float(latest["revenue"]), float(earliest["revenue"]), year_gap)
        eps_growth = cagr(float(latest["diluted_eps"]), float(earliest["diluted_eps"]), year_gap)
        quality = {
            "revenue_cagr_3y": revenue_cagr,
            "operating_margin_latest": float(latest["operating_income"]) / float(latest["revenue"]),
            "net_margin_latest": float(latest["net_income"]) / float(latest["revenue"]),
            "fcf_margin_latest": float(latest["free_cash_flow"]) / float(latest["revenue"]),
            "return_on_equity_latest": float(latest["net_income"]) / float(latest["stockholders_equity"]),
            "net_cash_to_revenue_latest": (float(latest["cash_and_equivalents"]) - float(latest["total_debt"])) / float(latest["revenue"]),
            "eps_growth_3y": eps_growth,
        }
        beta = risks[ticker]["beta_to_spy"]
        discount_rate = clamp(rf + beta * 0.05, 0.07, 0.14)
        base_growth = clamp(revenue_cagr, 0.02, 0.18)
        growths = {
            "base": base_growth,
            "bull": min(base_growth + 0.03, 0.22),
            "bear": max(base_growth - 0.04, 0.00),
        }
        terminals = {"base": 0.025, "bull": 0.035, "bear": 0.015}
        fair_values: dict[str, float] = {}
        for scenario, growth in growths.items():
            fcf = float(latest["free_cash_flow"])
            pv = 0.0
            for year in range(1, 6):
                projected = fcf * ((1.0 + growth) ** year)
                pv += projected / ((1.0 + discount_rate) ** year)
            year5 = fcf * ((1.0 + growth) ** 5)
            terminal = year5 * (1.0 + terminals[scenario]) / (discount_rate - terminals[scenario])
            pv += terminal / ((1.0 + discount_rate) ** 5)
            equity = pv + float(latest["cash_and_equivalents"]) - float(latest["total_debt"])
            fair_values[scenario] = equity / float(latest["diluted_shares"])
        latest_price = risks[ticker]["latest_price"]
        base_upside = fair_values["base"] / latest_price - 1.0
        margin_of_safety = (fair_values["base"] - latest_price) / fair_values["base"] if fair_values["base"] else -1.0
        score_base[ticker] = {
            **quality,
            **{k: risks[ticker][k] for k in ["total_return_252d", "annualized_volatility", "max_drawdown", "beta_to_spy", "sharpe_ratio"]},
            "base_upside_pct": base_upside,
            "margin_of_safety": margin_of_safety,
            "fcf_yield": float(latest["free_cash_flow"]) / (latest_price * float(latest["diluted_shares"])),
        }
        valuations[ticker] = {
            "ticker": ticker,
            "latest_price": latest_price,
            "base_fair_value": fair_values["base"],
            "bull_fair_value": fair_values["bull"],
            "bear_fair_value": fair_values["bear"],
            "base_upside_pct": base_upside,
            "margin_of_safety": margin_of_safety,
        }

    fields = list(next(iter(score_base.values())).keys())
    z_by_field = {field: dict(zip(tickers, zscores([score_base[t][field] for t in tickers]), strict=True)) for field in fields}

    score_rows: list[dict[str, Any]] = []
    for ticker in tickers:
        quality_component = float(np.mean([z_by_field[field][ticker] for field in [
            "revenue_cagr_3y",
            "operating_margin_latest",
            "fcf_margin_latest",
            "return_on_equity_latest",
            "net_cash_to_revenue_latest",
            "eps_growth_3y",
        ]]))
        risk_component = float(np.mean([
            z_by_field["total_return_252d"][ticker],
            z_by_field["sharpe_ratio"][ticker],
            z_by_field["max_drawdown"][ticker],
            -z_by_field["annualized_volatility"][ticker],
        ]))
        value_component = float(np.mean([
            z_by_field["base_upside_pct"][ticker],
            z_by_field["margin_of_safety"][ticker],
            z_by_field["fcf_yield"][ticker],
        ]))
        composite = 0.40 * quality_component + 0.25 * risk_component + 0.35 * value_component
        row = {
            "ticker": ticker,
            **{field: score_base[ticker][field] for field in [
                "revenue_cagr_3y",
                "operating_margin_latest",
                "net_margin_latest",
                "fcf_margin_latest",
                "return_on_equity_latest",
                "net_cash_to_revenue_latest",
                "eps_growth_3y",
                "total_return_252d",
                "annualized_volatility",
                "max_drawdown",
                "beta_to_spy",
                "sharpe_ratio",
            ]},
            "composite_score": composite,
            "base_upside_pct": score_base[ticker]["base_upside_pct"],
        }
        score_rows.append(row)

    score_rows.sort(key=lambda row: (-float(row["composite_score"]), -float(row["base_upside_pct"]), row["ticker"]))
    for index, row in enumerate(score_rows, start=1):
        row["rank"] = index
    score_by_ticker = {row["ticker"]: row for row in score_rows}

    for ticker, valuation in valuations.items():
        score_row = score_by_ticker[ticker]
        upside = float(valuation["base_upside_pct"])
        composite = float(score_row["composite_score"])
        max_dd = float(score_row["max_drawdown"])
        rank = int(score_row["rank"])
        if upside >= 0.15 and composite > 0:
            rec = "buy"
        elif upside < -0.25 or (rank >= len(tickers) - 1 and max_dd < -0.35):
            rec = "avoid"
        elif upside < -0.05 or max_dd < -0.45:
            rec = "trim"
        else:
            rec = "hold"
        valuation["recommendation"] = rec

    ranking = []
    for row in score_rows:
        ticker = row["ticker"]
        valuation = valuations[ticker]
        reason = (
            f"{ticker} ranks #{row['rank']} with composite score {round_float(row['composite_score'])}, "
            f"base upside {round_float(valuation['base_upside_pct'])}, and Sharpe {round_float(row['sharpe_ratio'])}."
        )
        ranking.append(
            {
                "rank": int(row["rank"]),
                "ticker": ticker,
                "composite_score": float(row["composite_score"]),
                "recommendation": str(valuation["recommendation"]),
                "primary_reason": reason,
            }
        )

    score_output_fields = [
        "ticker",
        "revenue_cagr_3y",
        "operating_margin_latest",
        "net_margin_latest",
        "fcf_margin_latest",
        "return_on_equity_latest",
        "net_cash_to_revenue_latest",
        "eps_growth_3y",
        "total_return_252d",
        "annualized_volatility",
        "max_drawdown",
        "beta_to_spy",
        "sharpe_ratio",
        "composite_score",
        "rank",
    ]
    score_output = [
        {field: int(row[field]) if field == "rank" else row[field] for field in score_output_fields}
        for row in sorted(score_rows, key=lambda row: row["ticker"])
    ]
    valuation_output = {
        "as_of_date": as_of_date.date().isoformat(),
        "risk_free_rate": rf,
        "securities": [valuations[ticker] for ticker in sorted(tickers)],
    }
    ranking_output = {
        "top_pick": ranking[0]["ticker"],
        "avoid_or_trim": [item["ticker"] for item in ranking if item["recommendation"] in {"avoid", "trim"}],
        "ranking": ranking,
    }
    memo = render_memo(company_names, valuation_output, ranking_output, score_by_ticker)
    return {
        "financial_metrics": fin_rows,
        "quality_risk_scores": score_output,
        "valuation": valuation_output,
        "investment_ranking": ranking_output,
        "research_memo": memo,
    }


def render_memo(
    company_names: dict[str, str],
    valuation: dict[str, Any],
    ranking: dict[str, Any],
    score_by_ticker: dict[str, dict[str, Any]],
) -> str:
    top3 = ranking["ranking"][:3]
    lines = [
        f"# Public Equity Quality, Risk, And Valuation Review",
        "",
        "## Data Sources",
        f"The analysis uses frozen SEC Company Facts, Yahoo Finance chart prices, and FRED DGS10 data through {valuation['as_of_date']}.",
        "",
        "## Financial Quality",
        "The strongest quality profiles are concentrated in the top-ranked companies after combining revenue growth, margins, cash generation, ROE, net cash, and EPS growth.",
        "",
        "## Market Risk",
        "Risk scores use 252 trading days of adjusted-close returns, SPY beta, annualized volatility, maximum drawdown, and excess-return Sharpe ratio.",
        "",
        "## Valuation",
        "The valuation section applies a five-year free-cash-flow DCF with base, bull, and bear scenarios, using DGS10 plus beta-adjusted equity risk premium as the discount-rate anchor.",
        "",
        "## Ranking And Recommendations",
        f"Top 3 tickers: {', '.join(item['ticker'] for item in top3)}.",
    ]
    valuation_by_ticker = {item["ticker"]: item for item in valuation["securities"]}
    for item in ranking["ranking"]:
        ticker = item["ticker"]
        score = score_by_ticker[ticker]
        val = valuation_by_ticker[ticker]
        lines.append(
            f"- Rank {item['rank']}: {ticker} ({company_names[ticker]}) is rated {item['recommendation']} "
            f"with composite score {round_float(item['composite_score'])}, base upside {round_float(val['base_upside_pct'])}, "
            f"max drawdown {round_float(score['max_drawdown'])}, and fair value {round_float(val['base_fair_value'], 2)}."
        )
    lines.append("")
    return "\n".join(lines)


def rounded_for_output(value: Any) -> Any:
    if isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        return round_float(value)
    return value


def write_outputs(output_root: Path = OUTPUT_ROOT) -> None:
    bundle = build_bundle()
    output_root.mkdir(parents=True, exist_ok=True)

    financial_fields = [
        "ticker",
        "company",
        "fiscal_year",
        "revenue",
        "operating_income",
        "net_income",
        "operating_cash_flow",
        "capital_expenditures",
        "free_cash_flow",
        "cash_and_equivalents",
        "total_debt",
        "stockholders_equity",
        "diluted_shares",
        "diluted_eps",
    ]
    with (output_root / "financial_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=financial_fields)
        writer.writeheader()
        for row in bundle["financial_metrics"]:
            writer.writerow({field: rounded_for_output(row[field]) for field in financial_fields})

    score_fields = [
        "ticker",
        "revenue_cagr_3y",
        "operating_margin_latest",
        "net_margin_latest",
        "fcf_margin_latest",
        "return_on_equity_latest",
        "net_cash_to_revenue_latest",
        "eps_growth_3y",
        "total_return_252d",
        "annualized_volatility",
        "max_drawdown",
        "beta_to_spy",
        "sharpe_ratio",
        "composite_score",
        "rank",
    ]
    with (output_root / "quality_risk_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=score_fields)
        writer.writeheader()
        for row in bundle["quality_risk_scores"]:
            writer.writerow({field: rounded_for_output(row[field]) for field in score_fields})

    for name in ["valuation", "investment_ranking"]:
        (output_root / f"{name}.json").write_text(
            json.dumps(round_nested(bundle[name]), indent=2, sort_keys=True),
            encoding="utf-8",
        )
    (output_root / "research_memo.md").write_text(bundle["research_memo"], encoding="utf-8")


def round_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: round_nested(item) for key, item in value.items()}
    if isinstance(value, list):
        return [round_nested(item) for item in value]
    return rounded_for_output(value)


if __name__ == "__main__":
    write_outputs()
