你现在处理的是一个二维四旋翼悬停建模任务。环境中提供了参数文件 `quadrotor_case.json` 和非线性仿真辅助脚本 `planar_quadrotor.py`。请围绕悬停平衡点建立局部线性模型，并检查它在小角度扰动与微小左右推力偏差下的短时预测质量。

系统状态与输入定义为：

- 状态 `x = [x, z, theta, vx, vz, omega]`
- 输入 `u = [u_left, u_right]`

连续时间非线性动力学为：

`dx/dt = vx`

`dz/dt = vz`

`dtheta/dt = omega`

`dvx/dt = -((u_left + u_right) / m) * sin(theta)`

`dvz/dt = ((u_left + u_right) / m) * cos(theta) - g`

`domega/dt = (arm_length / inertia) * (u_right - u_left)`

其中所有常数、悬停参考状态、验证扰动和误差阈值都在 `quadrotor_case.json` 中给出。

你需要完成的工作：

1. 根据质量 `m` 和重力 `g`，求出悬停平衡输入 `u*`，并写出参考状态 `x*`。
2. 在该悬停点对连续时间动力学求 Jacobian，得到 `(A_c, B_c)`。
3. 使用 `dt` 对局部连续模型做零阶保持离散化，得到 `(A_d, B_d)`。
4. 计算离散模型的可控性矩阵秩。
5. 使用 `validation_case` 中给出的初始状态偏移和恒定输入偏移，从悬停点附近滚动 `steps` 步：
   - 生成非线性模型轨迹；
   - 生成局部线性离散模型轨迹；
   - 计算 `max_position_error_norm`、`max_velocity_error_norm`、`max_attitude_error`、`rmse_by_state` 和 `final_abs_error`。
6. 写一句简洁结论，说明该局部模型是否满足悬停附近的短时近似要求。

只允许输出一个文件：

`artifacts/quadrotor_hover_linearization.json`

输出 JSON 必须包含以下结构：

```json
{
  "hover_equilibrium": {
    "reference_state": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "reference_input": [0.0, 0.0],
    "steady_state_residual": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  },
  "continuous_model": {
    "state_order": ["x", "z", "theta", "vx", "vz", "omega"],
    "input_order": ["u_left", "u_right"],
    "A": [[0.0]],
    "B": [[0.0]]
  },
  "discrete_model": {
    "dt": 0.04,
    "method": "zoh",
    "A": [[0.0]],
    "B": [[0.0]],
    "controllability_rank": 6
  },
  "validation": {
    "steps": 15,
    "initial_state": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "applied_input": [0.0, 0.0],
    "state_deviation": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "input_deviation": [0.0, 0.0],
    "nonlinear_rollout": [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]],
    "linear_rollout": [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]],
    "max_position_error_norm": 0.0,
    "max_velocity_error_norm": 0.0,
    "max_attitude_error": 0.0,
    "rmse_by_state": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "final_abs_error": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  },
  "acceptance": {
    "within_threshold": true,
    "thresholds": {
      "max_position_error_norm": 0.0,
      "max_velocity_error_norm": 0.0,
      "max_attitude_error": 0.0
    },
    "summary": "..."
  }
}
```

要求：

- `reference_state` 顺序必须是 `[x, z, theta, vx, vz, omega]`。
- `reference_input`、`applied_input` 和 `input_deviation` 都必须是长度为 2 的数组，顺序固定为 `[u_left, u_right]`。
- `steady_state_residual` 必须是把悬停参考点代回连续模型后得到的 6 维残差。
- `method` 必须写成 `"zoh"`。
- `nonlinear_rollout` 和 `linear_rollout` 中的每个元素都表示一步之后的完整 6 维状态。
- 不要修改环境中提供的输入资产。
