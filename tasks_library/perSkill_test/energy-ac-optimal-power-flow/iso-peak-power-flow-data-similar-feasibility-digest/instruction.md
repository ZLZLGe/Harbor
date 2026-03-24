你在独立系统运营商的晨间审查流程中，需要对一个峰时基础工况候选运行点做快速可行性摘要。不要重新优化，也不要调用外部求解器；只需读取 `network.json` 与 `candidate_operating_point.json`，按下面要求生成 `operations_feasibility_report.json`。

输入说明：

- `network.json` 是 MATPOWER 风格案例，包含 `bus`、`gen`、`branch`、`gencost` 等数组。
- `candidate_operating_point.json` 给出了这个候选工况下的全部母线电压幅值/相角，以及全部机组有功/无功出力。
- 母线编号不是连续编号，必须按实际 `BUS_I` 建立映射，不能把数组下标直接当母线编号。

只统计投运设备：

- 发电机仅统计 `GEN_STATUS = 1`。
- 支路仅统计 `BR_STATUS = 1`。
- `most_loaded_branches` 只考虑 `RATE_A > 0` 的支路。

支路潮流与功率失配都使用标准交流支路 π 模型。对每条支路 `[fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax]`：

- 当 `ratio` 为 0 时按 1.0 处理。
- 相移角 `angle` 需要从度转换为弧度。
- 串联导纳 `y = 1 / (r + jx) = g + jb`；若 `r = x = 0`，则取 `g = 0`、`b = 0`。
- 令 `t = ratio`、`shift = angle(rad)`，则

```text
P_ij = g*Vm_i^2/t^2 - Vm_i*Vm_j/t * (g*cos(Va_i - Va_j - shift) + b*sin(Va_i - Va_j - shift))
Q_ij = -(b + bc/2)*Vm_i^2/t^2 - Vm_i*Vm_j/t * (g*sin(Va_i - Va_j - shift) - b*cos(Va_i - Va_j - shift))

P_ji = g*Vm_j^2 - Vm_i*Vm_j/t * (g*cos(Va_j - Va_i + shift) + b*sin(Va_j - Va_i + shift))
Q_ji = -(b + bc/2)*Vm_j^2 - Vm_i*Vm_j/t * (g*sin(Va_j - Va_i + shift) - b*cos(Va_j - Va_i + shift))
```

- 两端表观功率分别为 `sqrt(P_ij^2 + Q_ij^2)` 与 `sqrt(P_ji^2 + Q_ji^2)`，单位都要换回 MVA。

按下面 JSON 结构输出：

```json
{
  "summary": {
    "total_load_MW": 0.0,
    "total_load_MVAr": 0.0,
    "total_generation_MW": 0.0,
    "total_generation_MVAr": 0.0,
    "total_losses_MW": 0.0
  },
  "reference_bus_check": {
    "reference_bus": 0,
    "angle_deg": 0.0,
    "target_angle_deg": 0.0,
    "tolerance_deg": 0.1,
    "abs_deviation_deg": 0.0,
    "within_tolerance": true
  },
  "most_loaded_branches": [
    {
      "from_bus": 0,
      "to_bus": 0,
      "loading_pct": 0.0,
      "flow_from_MVA": 0.0,
      "flow_to_MVA": 0.0,
      "limit_MVA": 0.0,
      "overload_MVA": 0.0
    }
  ],
  "feasibility_metrics": {
    "max_p_mismatch_MW": 0.0,
    "worst_p_mismatch_bus": 0,
    "max_q_mismatch_MVAr": 0.0,
    "worst_q_mismatch_bus": 0,
    "voltage_violations": {
      "count": 0,
      "max_violation_pu": 0.0,
      "worst_bus": 0
    },
    "generator_p_violations": {
      "count": 0,
      "max_violation_MW": 0.0,
      "worst_generator_id": 0
    },
    "generator_q_violations": {
      "count": 0,
      "max_violation_MVAr": 0.0,
      "worst_generator_id": 0
    },
    "branch_overloads": {
      "count": 0,
      "max_overload_MVA": 0.0,
      "worst_branch": {
        "from_bus": 0,
        "to_bus": 0
      }
    }
  }
}
```

补充要求：

- `summary.total_losses_MW = total_generation_MW - total_load_MW`。
- 参考母线取 `BUS_TYPE = 3` 的母线，检查其相角是否在 `0.1` 度容差内等于 0。
- `most_loaded_branches` 输出前 10 条重载支路，按 `loading_pct` 从高到低排序；若相同，再按 `from_bus`、`to_bus` 升序。
- 母线有功失配按 `sum(Pg@bus) - Pd - Gs*Vm^2 - sum(branch active outflows at bus)` 计算；无功失配按 `sum(Qg@bus) - Qd + Bs*Vm^2 - sum(branch reactive outflows at bus)` 计算。输出两者的最大绝对值及对应母线编号。
- 电压越限为 `max(0, Vm - Vmax, Vmin - Vm)`。
- 机组越界分别对有功和无功计算 `max(0, value - upper, lower - value)`。
- 支路过载为 `max(0, max(flow_from_MVA, flow_to_MVA) - RATE_A)`。
- 如果某类违规数量为 0，对应的 `max_*` 填 0.0，`worst_*` 填 0；本任务给定数据中并不会触发这些空集分支，但输出仍需满足该结构。
