请把这次校准任务迁移到“冬季结冰湖泊的冰下热结构”场景。

你可以使用这些输入资产：

1. `/root/glm3.nml`：模型配置文件。需要重点调整的参数是 `Kw`、`coef_mix_hyp`、`wind_factor`、`lw_factor`、`ch`。
2. `/root/inputs/winter_forcing.csv`：`2021-12-01` 到 `2022-03-15` 的逐日冬季强迫，字段为 `date`、`air_temp_c`、`shortwave_wm2`、`wind_speed_mps`、`snow_cm`、`inflow_temp_c`。
3. `/root/inputs/observed_under_ice_profiles.csv`：冰期实测温度剖面，字段为 `sample_date`、`depth_m`、`temperature_c`。
4. `/root/inputs/ice_event_targets.json`：观测整理出的关键冰期日期。
5. `glm` 命令：读取 `/root/glm3.nml` 和 forcing，生成 `/root/output/under_ice_profiles.csv`。

`/root/output/under_ice_profiles.csv` 必须包含这 4 列：

- `date`
- `depth_m`
- `temperature_c`
- `ice_thickness_m`

你的任务：

1. 反复调整 `/root/glm3.nml` 中上述 5 个参数并运行模型。
2. 用 `/root/inputs/observed_under_ice_profiles.csv` 与最终模型输出按采样日期和深度对齐后，同时满足：
   - `overall_profile_rmse_c <= 0.02`
   - `max_bottom_bias_c <= 0.02`
   - `mean_abs_two_degree_isotherm_bias_m <= 0.02`
   - `max_abs_two_degree_isotherm_bias_m <= 0.03`
3. 从最终模型输出的逐日剖面中按以下规则提取关键日期，并要求它们与 `/root/inputs/ice_event_targets.json` 完全一致：
   - `ice_onset_date`：第一个 `ice_thickness_m >= 0.05` 的日期。
   - `stable_inverse_onset_date`：第一个同时满足 `ice_thickness_m >= 0.05`、`bottom_temp - surface_temp >= 2.8`，且 `2.0` 摄氏度等温线深度 `>= 3.6 m` 的日期。
   - `peak_ice_date`：`ice_thickness_m` 达到全窗最大值的日期。
4. `2.0` 摄氏度等温线深度的定义如下：
   - 对每个剖面按 `depth_m` 升序排列。
   - 找到首个把 `2.0` 摄氏度夹在中间的相邻两层，按线性插值计算深度。
   - 如果某一层温度恰好等于 `2.0`，直接使用该层深度。
5. 保留最终可复现结果：
   - 最终参数必须写回 `/root/glm3.nml`
   - 最终模型输出必须存在于 `/root/output/under_ice_profiles.csv`
6. 把结果摘要写到 `/root/analysis/under_ice_fit_summary.json`

`/root/analysis/under_ice_fit_summary.json` 必须是合法 JSON，并且至少包含这些字段：

```json
{
  "lake": "North Star Bay",
  "simulation_window": {
    "start": "2021-12-01",
    "end": "2022-03-15"
  },
  "sampled_profile_dates": 8,
  "key_dates": {
    "observed_ice_onset": "2021-12-22",
    "simulated_ice_onset": "2021-12-22",
    "observed_stable_inverse_onset": "2021-12-28",
    "simulated_stable_inverse_onset": "2021-12-28",
    "observed_peak_ice_date": "2022-01-25",
    "simulated_peak_ice_date": "2022-01-25"
  },
  "fit_metrics": {
    "overall_profile_rmse_c": 0.0,
    "max_bottom_bias_c": 0.0,
    "mean_abs_two_degree_isotherm_bias_m": 0.0,
    "max_abs_two_degree_isotherm_bias_m": 0.0
  },
  "two_degree_isotherm_comparison": [
    {
      "sample_date": "2021-12-22",
      "observed_depth_m": 2.965035,
      "simulated_depth_m": 2.965035,
      "abs_error_m": 0.0,
      "observed_bottom_temp_c": 3.515803,
      "simulated_bottom_temp_c": 3.515803
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

- `sampled_profile_dates` 是 `observed_under_ice_profiles.csv` 中不同 `sample_date` 的总数。
- `two_degree_isotherm_comparison` 需要覆盖全部采样日期，并按 `sample_date` 升序排列。
- JSON 中报告的关键日期、误差、等温线深度和参数，必须与最终留在 `/root/glm3.nml` 里的参数重新运行模型后得到的结果一致，允许正常浮点舍入误差。
