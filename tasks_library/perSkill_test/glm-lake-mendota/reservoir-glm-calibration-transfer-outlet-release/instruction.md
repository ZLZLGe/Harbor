请把这次校准任务转到“水库夏季冷水团出流温度”场景。

你可以使用这些输入资产：

1. `/root/glm3.nml`：模型配置文件。需要重点调的参数是 `Kw`、`coef_mix_hyp`、`wind_factor`、`lw_factor`、`ch`。
2. `/root/inputs/reservoir_forcing.csv`：逐日气象与入流水温强迫，字段为 `date`、`air_temp_c`、`shortwave_wm2`、`wind_speed_mps`、`inflow_temp_c`。
3. `/root/inputs/release_schedule.csv`：逐日调度条件，字段为 `date`、`release_cms`、`withdrawal_depth_m`。
4. `/root/inputs/release_temperature_observed.csv`：逐日观测出流温度，字段为 `date`、`observed_release_temp_c`。
5. `glm` 命令：读取 `/root/glm3.nml` 和上述输入，并生成 `/root/output/release_temperature_daily.csv`。

你的任务：

1. 反复调整 `/root/glm3.nml` 中上述 5 个参数并运行模型。
2. 在 `2014-06-01` 到 `2014-09-08` 的调度窗口内，让模拟出流温度与观测对齐后同时满足：
   - RMSE 不高于 `0.08` 摄氏度
   - 最大绝对日误差不高于 `0.18` 摄氏度
   - 平均偏差 `mean(simulated - observed)` 的绝对值不高于 `0.05` 摄氏度
3. 保留最终可复现结果：
   - 最终参数必须写回 `/root/glm3.nml`
   - 最终模型输出必须存在于 `/root/output/release_temperature_daily.csv`
4. 把逐日拟合结果写到 `/root/reports/release_temperature_fit.csv`

`/root/reports/release_temperature_fit.csv` 必须满足：

1. CSV 必须恰好包含这 4 列，且列顺序一致：
   - `date`
   - `observed_release_temp_c`
   - `simulated_release_temp_c`
   - `abs_error_c`
2. 必须覆盖观测文件中的全部日期，每个日期恰好 1 行，并按日期升序排列。
3. `abs_error_c` 必须等于对应日期的绝对误差。
4. CSV 中报告的模拟温度与误差，必须和你最终留在 `/root/glm3.nml` 里的参数重新运行模型后得到的结果一致，允许正常浮点舍入误差。
