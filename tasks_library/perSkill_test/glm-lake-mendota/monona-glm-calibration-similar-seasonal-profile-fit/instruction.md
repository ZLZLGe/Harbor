请围绕 2012-01-01 到 2013-12-31 的 Lake Monona 温度剖面做一次短时窗校准。

你可以使用这些输入资产：

1. `/root/glm3.nml`：模型配置文件。需要重点调的参数是 `Kw`、`coef_mix_hyp`、`wind_factor`、`lw_factor`、`ch`。
2. `/root/inputs/monona_forcing.csv`：已经整理好的逐日气象强迫。
3. `/root/inputs/monona_sparse_profiles.csv`：稀疏实测温度剖面，字段为 `sample_date`、`depth_m`、`temperature_c`。
4. `glm` 命令：读取 `/root/glm3.nml` 并生成 `/root/output/monona_profiles.csv`。

你的任务：

1. 反复调整 `/root/glm3.nml` 中上述 5 个参数并运行模型。
2. 让模型输出与 `/root/inputs/monona_sparse_profiles.csv` 对齐后满足：
   - overall RMSE 不高于 `0.06` 摄氏度
   - 任一采样日期的 profile RMSE 不高于 `0.08` 摄氏度
3. 保留最终可复现结果：
   - 最终参数必须写回 `/root/glm3.nml`
   - 最终模型输出必须存在于 `/root/output/monona_profiles.csv`
4. 把结果摘要写到 `/root/results/monona_profile_calibration.json`

`/root/results/monona_profile_calibration.json` 必须是合法 JSON，并且至少包含这些字段：

```json
{
  "lake": "Monona",
  "simulation_window": {
    "start": "2012-01-01",
    "end": "2013-12-31"
  },
  "overall_rmse_c": 0.0,
  "max_profile_rmse_c": 0.0,
  "profile_count": 11,
  "calibrated_parameters": {
    "Kw": 0.0,
    "coef_mix_hyp": 0.0,
    "wind_factor": 0.0,
    "lw_factor": 0.0,
    "ch": 0.0
  },
  "profile_rmse_c": [
    {
      "sample_date": "2012-03-20",
      "rmse_c": 0.0
    }
  ]
}
```

说明：

- `profile_count` 指有多少个不同的 `sample_date` 被纳入 RMSE 统计。
- `profile_rmse_c` 需要覆盖全部采样日期。
- JSON 中报告的 RMSE 数值必须和你最终留在 `/root/glm3.nml` 里的参数重新运行模型后得到的结果一致，允许正常浮点误差。
