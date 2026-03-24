你现在处理的是一个孤岛微电网逆变器的小信号建模任务。环境中提供了参数文件 `microgrid_case.json`、负载调度表 `load_step_profile.csv`，以及一个非线性动力学辅助脚本 `microgrid_droop.py`。请围绕额定负载点建立局部线性模型，并检查它在一次小负载突变下对频率偏差与电压偏差的短时预测质量。

系统状态与输入定义为：

- 状态 `x = [delta_f_hz, delta_v_pu]`
- 输入 `u = [P_load_pu, Q_load_pu]`

连续时间非线性动力学为：

`ddelta_f_hz/dt = (-delta_f_hz - k_p * (P_load_pu * ((V_nom + delta_v_pu) / V_nom)^alpha_p * (1 + c_pf * delta_f_hz) - P_nom)) / tau_f`

`ddelta_v_pu/dt = (-delta_v_pu - k_q * (Q_load_pu * ((V_nom + delta_v_pu) / V_nom)^alpha_q * (1 + c_qf * delta_f_hz) - Q_nom)) / tau_v`

其中 `P_nom`、`Q_nom` 是额定负载点，其他常数都在 `microgrid_case.json` 中给出；`load_step_profile.csv` 按时间给出分段常值负载序列，每一行从该时刻起生效。

你需要完成的工作：

1. 读取额定负载点，写出参考状态 `x*` 与参考输入 `u*`，并计算把该工作点代回连续模型后的 `steady_state_residual`。
2. 在该额定负载点对连续时间动力学求 Jacobian，得到 `(A_c, B_c)`。
3. 使用 `dt` 对局部连续模型做零阶保持离散化，得到 `(A_d, B_d)`，并给出离散极点。
4. 使用 `validation_case` 中的 `initial_state`，按照 `load_step_profile.csv` 的分段常值负载滚动 `steps` 步：
   - 生成非线性模型轨迹；
   - 生成局部线性离散模型轨迹；
   - 对每个步长记录所施加的负载；
   - 计算 `max_abs_frequency_gap_hz`、`max_abs_voltage_gap_pu`、`frequency_nadir_gap_hz`、`voltage_nadir_gap_pu` 和 `final_state_gap`。
5. 写一句简洁结论，说明该局部模型是否能近似描述这次小负载突变下的频率和电压偏差。

只允许输出一个文件：

`artifacts/microgrid_droop_linearization.json`

输出 JSON 必须包含以下结构：

```json
{
  "nominal_operating_point": {
    "state_order": ["delta_f_hz", "delta_v_pu"],
    "input_order": ["P_load_pu", "Q_load_pu"],
    "reference_state": [0.0, 0.0],
    "reference_input": [0.0, 0.0],
    "steady_state_residual": [0.0, 0.0]
  },
  "continuous_small_signal_model": {
    "A": [[0.0, 0.0], [0.0, 0.0]],
    "B": [[0.0, 0.0], [0.0, 0.0]]
  },
  "discrete_small_signal_model": {
    "dt": 0.05,
    "method": "zoh",
    "A": [[0.0, 0.0], [0.0, 0.0]],
    "B": [[0.0, 0.0], [0.0, 0.0]],
    "eigenvalues": [
      {"real": 0.0, "imag": 0.0},
      {"real": 0.0, "imag": 0.0}
    ]
  },
  "load_step_validation": {
    "steps": 20,
    "initial_state": [0.0, 0.0],
    "applied_load_sequence": [
      {"time": 0.0, "loads": [0.0, 0.0]}
    ],
    "nonlinear_rollout": [
      {"time": 0.05, "frequency_deviation_hz": 0.0, "voltage_deviation_pu": 0.0}
    ],
    "linear_rollout": [
      {"time": 0.05, "frequency_deviation_hz": 0.0, "voltage_deviation_pu": 0.0}
    ],
    "max_abs_frequency_gap_hz": 0.0,
    "max_abs_voltage_gap_pu": 0.0,
    "frequency_nadir_gap_hz": 0.0,
    "voltage_nadir_gap_pu": 0.0,
    "final_state_gap": [0.0, 0.0]
  },
  "assessment": {
    "within_tolerance": true,
    "thresholds": {
      "max_abs_frequency_gap_hz": 0.0,
      "max_abs_voltage_gap_pu": 0.0,
      "frequency_nadir_gap_hz": 0.0,
      "voltage_nadir_gap_pu": 0.0
    },
    "summary": "..."
  }
}
```

要求：

- `reference_state` 顺序必须是 `[delta_f_hz, delta_v_pu]`。
- `reference_input` 和 `loads` 的顺序都固定为 `[P_load_pu, Q_load_pu]`。
- `steady_state_residual` 必须是把额定负载点代回连续模型后得到的 2 维残差。
- `method` 必须写成 `"zoh"`。
- `eigenvalues` 必须按离散极点的 `real` 升序排列；如果 `real` 相同，则按 `imag` 升序排列。
- `applied_load_sequence` 中每个元素都表示该积分区间起点时刻采用的负载。
- `nonlinear_rollout` 和 `linear_rollout` 中每个元素都表示一步之后的完整 2 维状态。
- 不要修改环境中提供的输入资产。
