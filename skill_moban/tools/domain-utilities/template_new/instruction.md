You are supporting a corporate development and launch-operations team that is entering a new market segment and needs to decide which domains are worth acquiring now, which ones should stay on a watchlist, and which ones must be rejected. The candidate pool is realistic and the final decision must be justified by frozen registration, DNS, archive, authority, and legal evidence. Solve this task step by step. Check available guidance, tools or procedures to guarantee a correct answer.

Input data are stored under `/app/data/`.

The main materials include:
- `market_brief.md`
- `candidate_domains.csv`
- `scoring_policy.md`
- `authority_metrics.csv`
- `sales_comps.csv`
- `trademark_flags.csv`
- `archive_summaries/`
- `service_catalog.md`

Some frozen lookup endpoints may also be exposed inside the container. If they exist, they are documented in `/app/data/service_catalog.md` and are part of the real task chain.

Your task:
1. Evaluate every candidate domain in the provided pool for market fit, authority, commercial intent, and legal or brand risk using only the provided materials and local lookup chain.
2. Decide whether each candidate should be classified as `buy_now`, `monitor`, or `reject`.
3. Produce a ranked acquisition recommendation for the best immediately actionable domains.
4. Estimate a defensible `price_ceiling_usd` for each non-rejected candidate using the provided comparable-sales materials and policy constraints.
5. Record concise machine-readable evidence for every decision so the launch team can audit the result later.

You are required to generate `/app/output/opportunity_report.json`. Please follow the following format. Round all numeric values to 2 decimals. Sort arrays by `domain` ascending unless another order is explicitly required. Use `null` if a value cannot be derived from the provided materials.

{
  "segment": "",
  "top_pick": "",
  "buy_now_ranked": ["", "", ""],
  "evaluations": [
    {
      "domain": "",
      "status": "buy_now or monitor or reject",
      "market_fit_score": ,
      "authority_score": ,
      "commercial_intent_score": ,
      "legal_risk_score": ,
      "price_ceiling_usd": ,
      "total_score": ,
      "reason_codes": [""],
      "evidence": [
        {
          "source": "",
          "key": "",
          "value": ""
        }
      ]
    }
  ]
}

Output rules:
- `buy_now_ranked` must contain exactly 3 domains.
- `buy_now_ranked` must be sorted by `total_score` descending and then `domain` ascending.
- `top_pick` must be the first item of `buy_now_ranked`.
- `evaluations` must contain every candidate domain exactly once.
- `reason_codes` must be selected from the policy, legal, or risk materials provided under `/app/data/`.
- `evidence` must contain at least 2 items for each domain.
- `price_ceiling_usd` must be `null` for domains classified as `reject`.
- Do not hallucinate or guess registration, DNS, archive, authority, legal, or pricing evidence.

Notes:
- The task must be solved against the real provided data and any documented local lookup services inside the container.
- You may write helper scripts or intermediate files if needed, but the final graded artifact is only `/app/output/opportunity_report.json`.
- Do not replace the real lookup chain with mock data, stub responses, or hardcoded final answers.
- Do not modify or delete the provided candidate pool, frozen datasets, or service definitions to avoid difficult cases.
- Do not remove candidates, skip difficult cases, or rewrite the task into a simpler one.
- The solution is allowed to use any implementation approach, but the final result must reflect the real evidence and business constraints.
