你现在处理的是一个 6 段卷对卷张力系统的双工况建模任务。环境中提供了动力学代码 `r2r_simulator.py` 和工况说明 `dual_regime_config.json`。请围绕换辊前后的两个参考工况，分别建立局部线性模型，并用短时间窗验证线性模型是否能近似预测真实非线性系统的状态变化。

系统连续时间动力学为：

`dT_i/dt = (EA/L) * (v_i - v_{i-1}) + (1/L) * (v_{i-1} * T_{i-1} - v_i * T_i)`

`dv_i/dt = (R^2/J) * (T_{i+1} - T_i) + (R/J) * u_i - (fb/J) * v_i`

其中状态为 `[T1..T6, v1..v6]`，输入为 `[u1..u6]`。

你需要完成的工作：

1. 根据 `dual_regime_config.json` 中的两个参考张力工况，求出每个工况对应的参考速度 `v_ref`、参考状态 `x_ref` 和参考输入 `u_ref`。
2. 在两个工况上分别求连续时间 Jacobian，得到 `(A_c, B_c)`。
3. 用任务时间步长 `dt` 将两个连续模型按前向 Euler 方法离散化，得到 `(A_d, B_d)`，即

`A_d = I + dt * A_c`

`B_d = dt * B_c`
4. 对 `dual_regime_config.json` 中给出的每个验证案例：
   - 使用给定的初始状态偏移和恒定输入偏移；
   - 从该工况的参考点出发，滚动 `steps` 步；
   - 同时生成非线性模型轨迹和局部线性离散模型轨迹，其中线性轨迹按同一个前向 Euler 离散模型推进；
   - 计算 `max_abs_state_error`、`mean_abs_tension_error`、`mean_abs_velocity_error`。
5. 比较两个工况下得到的模型差异，并给出一句简洁结论，说明两个局部模型在短时间窗内是否满足近似要求。

只允许输出一个文件：

`artifacts/r2r_dual_regime_linearization.json`

输出 JSON 必须包含以下结构：

```json
{
  "dt": 0.01,
  "regimes": {
    "pre_change": {
      "reference_state": [12 floats],
      "reference_input": [6 floats],
      "continuous_model": {
        "A": [[12x12 floats]],
        "B": [[12x6 floats]]
      },
      "discrete_model": {
        "A": [[12x12 floats]],
        "B": [[12x6 floats]]
      },
      "validation": {
        "steps": 8,
        "initial_state": [12 floats],
        "control_input": [6 floats],
        "nonlinear_rollout": [[12 floats], "..."],
        "linear_rollout": [[12 floats], "..."],
        "max_abs_state_error": 0.0,
        "mean_abs_tension_error": 0.0,
        "mean_abs_velocity_error": 0.0
      }
    },
    "post_change": {
      "reference_state": [12 floats],
      "reference_input": [6 floats],
      "continuous_model": {
        "A": [[12x12 floats]],
        "B": [[12x6 floats]]
      },
      "discrete_model": {
        "A": [[12x12 floats]],
        "B": [[12x6 floats]]
      },
      "validation": {
        "steps": 8,
        "initial_state": [12 floats],
        "control_input": [6 floats],
        "nonlinear_rollout": [[12 floats], "..."],
        "linear_rollout": [[12 floats], "..."],
        "max_abs_state_error": 0.0,
        "mean_abs_tension_error": 0.0,
        "mean_abs_velocity_error": 0.0
      }
    }
  },
  "comparison": {
    "max_abs_continuous_A_delta": 0.0,
    "max_abs_continuous_B_delta": 0.0,
    "max_abs_discrete_A_delta": 0.0,
    "max_abs_discrete_B_delta": 0.0,
    "validation_passed": true,
    "summary": "..."
  }
}
```

要求：

- `reference_state` 必须按 `[T1..T6, v1..v6]` 排列。
- `nonlinear_rollout` 和 `linear_rollout` 中每个元素都表示一步之后的完整 12 维状态。
- 两个工况都必须写入完整结果，不能只提交其中一个。
- 不要修改环境中提供的输入资产。
