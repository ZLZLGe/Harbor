You are supporting a transmission reliability desk that performs a fast N-1 transfer screen after each candidate corridor outage. A solved post-contingency voltage snapshot is already available for each outage scenario, and your job is to recompute the surviving branch flows and identify which outage is most dangerous.

Use `contingency_cases.json` as the only input. It provides:

- one common branch list with MVA ratings
- one post-contingency voltage snapshot per outage scenario
- one branch outage per scenario

For every scenario, evaluate only the surviving branches, compute the bidirectional AC branch flows and apparent power magnitudes, then identify the single worst surviving branch for that scenario. Write `/root/contingency_screen.json` with the exact structure below. Use MW, MVAr, and MVA for power quantities.

- Sort `scenario_results` by descending `max_overload_MVA`, then descending `max_loading_pct`, then ascending `scenario_id`.
- Set `severity_rank` from that sorted order.
- Within each scenario, `worst_branch` is the surviving branch with the largest `overload_MVA`; if several branches tie, use the larger `loading_pct`, then the lexicographically smaller branch `id`.

```json
{
  "study_id": "delta-transfer-screen-2031q3",
  "summary": {
    "scenario_count": 4,
    "scenarios_with_overloads": 3,
    "most_dangerous_scenario_id": "OUT_L13",
    "most_dangerous_outaged_branch_id": "L13",
    "overall_worst_branch_id": "T23",
    "overall_worst_loading_pct": 110.404662,
    "overall_worst_overload_MVA": 23.410489
  },
  "scenario_results": [
    {
      "severity_rank": 1,
      "scenario_id": "OUT_L13",
      "outaged_branch_id": "L13",
      "surviving_branch_count": 4,
      "overloaded_branch_count": 2,
      "max_loading_pct": 110.404662,
      "max_overload_MVA": 23.410489,
      "worst_branch": {
        "id": "T23",
        "from_bus": 12,
        "to_bus": 13,
        "p_from_MW": 241.711097,
        "q_from_MVAr": 57.301978,
        "s_from_MVA": 248.410489,
        "p_to_MW": -235.773118,
        "q_to_MVAr": -17.718259,
        "s_to_MVA": 236.437941,
        "limit_MVA": 225.0,
        "loading_pct": 110.404662,
        "overload_MVA": 23.410489
      }
    }
  ]
}
```
