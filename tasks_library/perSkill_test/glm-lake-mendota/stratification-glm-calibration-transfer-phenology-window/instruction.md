请把这次校准任务转成“单季分层物候诊断”场景，而不是逐点温度 RMSE。

你可以使用这些输入资产：

1. `/root/glm3.nml`：模型配置文件。重点调整参数仍然是 `Kw`、`coef_mix_hyp`、`wind_factor`、`lw_factor`、`ch`。
2. `/root/inputs/seasonal_forcing.csv`：2015-04-01 到 2015-10-31 的逐日强迫，字段为 `date`、`air_temp_c`、`shortwave_wm2`、`wind_speed_mps`、`cloud_fraction`。
3. `/root/inputs/observed_stratification_profiles.csv`：2015 年单个暖季的实测剖面，字段为 `sample_date`、`depth_m`、`temperature_c`。
4. `glm` 命令：读取 `/root/glm3.nml` 与 forcing，生成 `/root/output/seasonal_profiles.csv`。

你的任务：

1. 反复调整 `/root/glm3.nml` 中上述 5 个参数并运行模型。
2. 用观测剖面和最终模拟结果都按下面同一套规则提取诊断指标：
   - 对每个剖面按 `depth_m` 升序排列。
   - 相邻两层的梯度定义为 `(temp_upper - temp_lower) / (depth_lower - depth_upper)`。
   - `thermocline_depth_m` 定义为最大梯度对应两层深度的中点。
   - 只有当表底温差 `surface_bottom_delta_c >= 1.5` 且最大梯度 `>= 0.3` 时，该剖面才算“分层”。
   - `onset` 定义为本季第一个分层观测日期。
   - `breakdown` 定义为 `2015-09-01` 及之后、第一个不再分层且发生在当季已分层之后的观测日期。
3. 在最终结果里同时满足：
   - 模拟的 `onset` 必须与观测 `onset` 完全一致
   - 模拟的 `breakdown` 必须与观测 `breakdown` 完全一致
   - `matched_profile_count` 必须等于全部分层观测剖面数
   - 分层剖面的 `mean_abs_error_m` 不高于 `0.35`
   - 分层剖面的 `max_abs_error_m` 不高于 `0.80`
   - 全部观测日期上的 `surface_bottom_delta_rmse_c` 不高于 `0.18`
4. 保留最终可复现结果：
   - 最终参数必须写回 `/root/glm3.nml`
   - 最终模型输出必须存在于 `/root/output/seasonal_profiles.csv`，并覆盖 `2015-04-01` 到 `2015-10-31` 的全部日期
5. 把事件级摘要写到 `/root/diagnostics/stratification_phenology_report.json`

`/root/diagnostics/stratification_phenology_report.json` 必须是合法 JSON，并且至少包含这些字段。下面的 JSON 只示意字段结构与数据类型，示例值不是正确答案，实际内容必须根据你最终保留的参数和模型输出来计算：

```json
{
  "lake": "Pine Ridge Lake",
  "season": {
    "start": "2015-04-01",
    "end": "2015-10-31"
  },
  "sampled_profile_dates": 0,
  "event_dates": {
    "observed_onset": "YYYY-MM-DD",
    "simulated_onset": "YYYY-MM-DD",
    "observed_breakdown": "YYYY-MM-DD",
    "simulated_breakdown": "YYYY-MM-DD",
    "onset_error_days": 0,
    "breakdown_error_days": 0
  },
  "thermocline_depth_metrics": {
    "matched_profile_count": 0,
    "mean_abs_error_m": 0.0,
    "max_abs_error_m": 0.0
  },
  "surface_bottom_delta_rmse_c": 0.0,
  "thermocline_depth_comparison": [
    {
      "sample_date": "YYYY-MM-DD",
      "observed_depth_m": 0.0,
      "simulated_depth_m": 0.0,
      "abs_error_m": 0.0,
      "observed_surface_bottom_delta_c": 0.0,
      "simulated_surface_bottom_delta_c": 0.0
    }
  ],
  "calibrated_parameters": {
    "Kw": 0.0,
    "coef_mix_hyp": 0.0,
    "wind_factor": 0.0,
    "lw_factor": 0.0,
    "ch": 0.0
  }
}
```

说明：

- `sampled_profile_dates` 是 `observed_stratification_profiles.csv` 里不同 `sample_date` 的总数。
- `thermocline_depth_comparison` 只包含“观测与模拟都被判定为分层”的日期，且必须覆盖全部分层观测日期。
- JSON 中报告的日期、误差和参数，必须与最终留在 `/root/glm3.nml` 里的参数重新运行模型后得到的结果一致，允许正常浮点舍入误差。
