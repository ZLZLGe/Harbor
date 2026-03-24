你在电网模型治理小组里负责上线前的数据质检。请扫描 `cases/` 目录下的全部案例文件，读取每个 MATPOWER 风格 JSON 案例，并生成统一的 `case_lint_report.json`。

输入说明：

- 每个案例文件都包含 `baseMVA`、`bus`、`gen`、`branch`、`gencost`。
- `bus`、`gen`、`branch` 的字段位置沿用 MATPOWER 常见定义：
  - `bus`: `[BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, VM, VA, BASE_KV, ZONE, VMAX, VMIN]`
  - `gen`: `[GEN_BUS, PG, QG, QMAX, QMIN, VG, MBASE, GEN_STATUS, PMAX, PMIN]`
  - `branch`: `[F_BUS, T_BUS, R, X, B, RATE_A, RATE_B, RATE_C, TAP, SHIFT, BR_STATUS, ANGMIN, ANGMAX]`
- 母线编号不保证连续，也不保证按编号排序，必须按实际 `BUS_I` 处理。
- 发电机编号与支路编号都使用各自数组中的 1-based 行号。

需要检查的问题：

1. `duplicate_bus_ids`
   - 找出 `bus` 中重复出现的 `BUS_I`。
   - 只输出去重后的母线编号，并按升序排列。
2. `missing_reference_bus`
   - 若 `BUS_TYPE = 3` 的母线数量为 0，则记为 `true`，否则为 `false`。
   - 另外输出全部 `reference_bus_ids`，按升序排列。
3. `generator_buses_missing`
   - 对每台发电机，若 `GEN_BUS` 不在 `bus` 的 `BUS_I` 集合中，则记为问题。
4. `branch_endpoints_missing`
   - 对每条支路，若 `F_BUS` 或 `T_BUS` 任一端点不在 `bus` 的 `BUS_I` 集合中，则记为问题。
5. `isolated_online_subnetworks`
   - 只基于“在线设备”做拓扑审计：
     - 在线支路满足 `BR_STATUS = 1` 且两个端点都存在。
     - 在线发电机满足 `GEN_STATUS = 1` 且 `GEN_BUS` 存在。
   - 用这些在线支路构造无向图。
   - 参与连通性分析的母线集合为：
     - 任一在线有效支路的端点；
     - 或挂接了在线有效发电机的母线。
   - 若该集合形成多个连通分量，则把其中“主连通分量”以外的所有分量记为孤立子网。
   - 主连通分量的判定顺序为：
     1. `bus_count` 更大者优先；
     2. 若相同，`online_generator_count` 更大者优先；
     3. 若仍相同，最小母线编号更小者优先。
   - 每个孤立子网需要输出：
     - `subnetwork_id`
     - `bus_ids`
     - `bus_count`
     - `online_generator_ids`
     - `online_generator_count`
     - `online_branch_ids`
     - `online_branch_count`
6. 额定值问题：
   - `nonpositive_branch_ratings`: 所有 `RATE_A <= 0` 的支路。
   - `nonpositive_generator_pmax`: 所有 `PMAX <= 0` 的发电机。
   - `invalid_generator_q_ranges`: 所有 `QMAX <= QMIN` 的发电机。

输出 JSON 结构必须为：

```json
{
  "portfolio_summary": {
    "case_count": 0,
    "cases_with_any_issue": 0,
    "total_issue_count": 0,
    "issue_type_counts": {
      "duplicate_bus_ids": 0,
      "missing_reference_bus": 0,
      "generator_buses_missing": 0,
      "branch_endpoints_missing": 0,
      "isolated_online_subnetworks": 0,
      "nonpositive_branch_ratings": 0,
      "nonpositive_generator_pmax": 0,
      "invalid_generator_q_ranges": 0
    }
  },
  "cases": [
    {
      "case_id": "",
      "source_file": "cases/example.json",
      "bus_count": 0,
      "generator_count": 0,
      "branch_count": 0,
      "reference_bus_ids": [0],
      "issue_counts": {
        "duplicate_bus_ids": 0,
        "missing_reference_bus": 0,
        "generator_buses_missing": 0,
        "branch_endpoints_missing": 0,
        "isolated_online_subnetworks": 0,
        "nonpositive_branch_ratings": 0,
        "nonpositive_generator_pmax": 0,
        "invalid_generator_q_ranges": 0,
        "total": 0
      },
      "issues": {
        "duplicate_bus_ids": [0],
        "missing_reference_bus": false,
        "generator_buses_missing": [
          {
            "generator_id": 0,
            "bus": 0
          }
        ],
        "branch_endpoints_missing": [
          {
            "branch_id": 0,
            "from_bus": 0,
            "to_bus": 0
          }
        ],
        "isolated_online_subnetworks": [
          {
            "subnetwork_id": "island_1",
            "bus_ids": [0],
            "bus_count": 0,
            "online_generator_ids": [0],
            "online_generator_count": 0,
            "online_branch_ids": [0],
            "online_branch_count": 0
          }
        ],
        "nonpositive_branch_ratings": [
          {
            "branch_id": 0,
            "from_bus": 0,
            "to_bus": 0,
            "rateA": 0.0
          }
        ],
        "nonpositive_generator_pmax": [
          {
            "generator_id": 0,
            "bus": 0,
            "pmax_MW": 0.0
          }
        ],
        "invalid_generator_q_ranges": [
          {
            "generator_id": 0,
            "bus": 0,
            "qmin_MVAr": 0.0,
            "qmax_MVAr": 0.0
          }
        ]
      }
    }
  ]
}
```

补充要求：

- `cases` 按源文件名的字典序排序。
- `case_id` 使用文件名去掉 `.json` 之后的部分。
- 每个案例的 `issue_counts.total` 等于该案例所有问题项数量之和，其中 `missing_reference_bus = true` 记 1，否则记 0。
- `portfolio_summary.issue_type_counts` 是对所有案例同类问题数量的总和。
- `portfolio_summary.total_issue_count` 等于 `issue_type_counts` 各字段之和。
- `portfolio_summary.cases_with_any_issue` 是 `issue_counts.total > 0` 的案例数。
- 每个问题列表都按编号升序排序；`isolated_online_subnetworks` 按主连通分量剔除后的优先级顺序依次编号为 `island_1`、`island_2`、……
