你现在处理的是一个带冷却夹套的连续搅拌釜反应器建模任务。环境中提供了参数文件 `cstr_case.json` 和一个非线性仿真辅助脚本 `cstr_reactor.py`。请围绕标称转化率工作点，建立局部线性模型并检查它在小幅冷却流量扰动下的短时有效性。

反应器状态为 `x = [C_A, T]`，输入为 `u = [q_c]`，其中：

- `C_A` 为釜内反应物浓度
- `T` 为釜内温度
- `q_c` 为冷却剂流量

连续时间非线性模型为：

`r(C_A, T) = k0 * exp(-E_over_R / T) * C_A`

`dC_A/dt = (C_Af - C_A) / tau - r(C_A, T)`

`dT/dt = (T_f - T) / tau + heat_release_gain * r(C_A, T) - cooling_gain * q_c * (T - T_c)`

你需要完成的工作：

1. 根据 `cstr_case.json` 中的 `target_conversion` 和 `nominal_temperature`，求出工作点浓度 `C_A*`、温度 `T*` 和稳态冷却流量 `q_c*`。
2. 在该工作点对连续时间动力学求 Jacobian，得到 `(A_c, B_c)`。
3. 使用 `dt` 对局部连续模型做零阶保持离散化，得到 `(A_d, B_d)`。
4. 使用 `validation_case` 中给出的初始状态偏移和恒定输入偏移，从工作点附近滚动 `steps` 步：
   - 生成非线性模型轨迹；
   - 生成局部线性离散模型轨迹；
   - 计算 `max_abs_error`、`rmse_by_state` 和 `final_abs_error`。
5. 写一句简洁结论，说明该局部模型是否满足短时近似要求。

只允许输出一个文件：

`artifacts/cstr_operating_point_linearization.json`

输出 JSON 必须包含以下结构：

```json
{
  "operating_point": {
    "target_conversion": 0.55,
    "reference_state": [0.0, 0.0],
    "reference_input": [0.0],
    "steady_state_residual": [0.0, 0.0]
  },
  "continuous_model": {
    "state_order": ["C_A", "T"],
    "input_order": ["q_c"],
    "A": [[0.0, 0.0], [0.0, 0.0]],
    "B": [[0.0], [0.0]]
  },
  "discrete_model": {
    "dt": 0.05,
    "method": "zoh",
    "A": [[0.0, 0.0], [0.0, 0.0]],
    "B": [[0.0], [0.0]],
    "eigenvalues": [
      {"real": 0.0, "imag": 0.0},
      {"real": 0.0, "imag": 0.0}
    ]
  },
  "validation": {
    "steps": 14,
    "initial_state": [0.0, 0.0],
    "applied_input": [0.0],
    "input_deviation": [0.0],
    "nonlinear_rollout": [[0.0, 0.0]],
    "linear_rollout": [[0.0, 0.0]],
    "max_abs_error": 0.0,
    "rmse_by_state": [0.0, 0.0],
    "final_abs_error": [0.0, 0.0]
  },
  "quality_summary": {
    "short_horizon_match": true,
    "thresholds": {
      "max_abs_error": 0.0,
      "temperature_rmse": 0.0
    },
    "summary": "..."
  }
}
```

要求：

- `reference_state` 顺序必须是 `[C_A, T]`。
- `reference_input`、`applied_input` 和 `input_deviation` 都必须是一维数组，即使只有一个输入。
- `steady_state_residual` 必须是把工作点代回连续模型后得到的两个残差。
- `nonlinear_rollout` 和 `linear_rollout` 中的每个元素都表示一步之后的完整 2 维状态。
- `method` 必须写成 `"zoh"`。
- 不要修改环境中提供的输入资产。
