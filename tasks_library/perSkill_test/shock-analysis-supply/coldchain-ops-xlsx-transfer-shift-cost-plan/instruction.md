你需要基于本地提供的冷链仓配模板工作簿和 4 份输入表，完成一个周度排班成本工作簿，并将结果保存为主文件名为 `coldchain-ops-plan`、且使用标准电子表格工作簿扩展名的文件。

可用输入文件：
- `coldchain-ops-template` 加标准电子表格文件扩展名的模板工作簿：包含目标工作表结构，以及 `Hourly_Load` 和 `Labor_Schedule` 的日期/小时骨架。
- `store_daily_demand.csv`：门店每日需求。
- `warehouse_shifts.csv`：仓库班次定义。
- `equipment_power_curve.csv`：小时设备功率曲线。
- `tou_tariff_template.csv`：分时电价模板。

模板中包含 9 个工作表：
- `Planner`：已预填产能、毛利、固定成本和小时负荷分布参数。
- `Store_Demand`：导入门店每日需求。
- `Shift_Definitions`：导入班次定义。
- `Power_Curve`：导入设备功率曲线。
- `Tariff_Template`：导入分时电价。
- `Hourly_Load`：需要补齐小时负荷、电量和电费。
- `Labor_Schedule`：需要补齐各日各班次的人力安排和超时成本。
- `Cost_Summary`：需要汇总周度用电与人工成本。
- `Profit_Bridge`：需要给出周度利润桥摘要。

请在模板基础上完成以下内容，且需要保留公式，不要把应由公式计算的结果改成手填常数：

1. 先把 4 个 CSV 的内容完整导入对应输入工作表，并保留原表头。

2. `Hourly_Load` 的 A:B 列日期和小时已经预填，请补齐 C:M 列（第 2 行到第 169 行）：
- C 列 `Total_Daily_Cases`：按日期汇总 `Store_Demand` 中当日所有门店需求。
- D 列 `Load_Share`：按小时从 `Planner` 的小时负荷分布表取值。
- E 列 `Hourly_Cases = Total_Daily_Cases * Load_Share`。
- F:I 列：按小时从 `Power_Curve` 取回 `Base_Refrigeration_kWh`、`Dock_Door_kWh`、`Handling_kWh_per_Case`、`Battery_Charge_kWh`。
- J 列 `Total_kWh = Base_Refrigeration_kWh + Dock_Door_kWh + Battery_Charge_kWh + Hourly_Cases * Handling_kWh_per_Case`。
- K:L 列：按小时从 `Tariff_Template` 取回 `Tariff_Period` 和 `Rate_per_kWh`。
- M 列 `Electricity_Cost = Total_kWh * Rate_per_kWh`。

3. `Labor_Schedule` 的 A:B 列日期和班次编号已经预填，请补齐 C:O 列（第 2 行到第 22 行）：
- C:F 列：按 `Shift_ID` 从 `Shift_Definitions` 取回 `Start_Hour`、`End_Hour`、`Shift_Length`、`Base_Headcount`，其中 `Shift_Length = End_Hour - Start_Hour`。
- G 列 `Shift_Cases`：汇总同一天且小时满足 `>= Start_Hour` 且 `< End_Hour` 的 `Hourly_Load[Hourly_Cases]`。
- H 列 `Required_Handlers = ROUNDUP(Shift_Cases / Shift_Length / Cases_per_Handler_Hour, 0)`。
- I 列 `Scheduled_Headcount = MAX(Base_Headcount, Required_Handlers + Supervisor_Buffer_Headcount)`。
- J 列 `Scheduled_Hours = Scheduled_Headcount * Shift_Length`。
- K 列 `Overtime_Hours = Scheduled_Headcount * MAX(Shift_Length - Regular_Hours, 0)`。
- L 列 `Hourly_Wage`：按 `Shift_ID` 取回。
- M 列 `Base_Labor_Cost = Scheduled_Hours * Hourly_Wage`。
- N 列 `Overtime_Premium = Overtime_Hours * Hourly_Wage * (Overtime_Multiplier - 1)`。
- O 列 `Total_Labor_Cost = Base_Labor_Cost + Overtime_Premium`。

4. 在 `Cost_Summary` 中补齐 B2:B12：
- B2：周度 `Total Cases`。
- B3：周度 `Total kWh`。
- B4:B7：分别汇总 `OffPeak`、`Shoulder`、`Peak`、`Critical` 四个分时段的电费。
- B8：周度 `Base Labor Cost`。
- B9：周度 `Overtime Premium`。
- B10：周度 `Total Labor Cost`。
- B11：周度 `Total Electricity Cost`。
- B12：周度 `Total Operating Cost`。

5. 在 `Profit_Bridge` 中补齐 B2:B7：
- B2：`Weekly Gross Margin = Total Cases * Gross_Margin_per_Case`。
- B3：`- Base Labor Cost`。
- B4：`- Overtime Premium`。
- B5：`- Electricity Cost`。
- B6：`- Fixed Site Cost`。
- B7：`Weekly Operating Profit`。

输出要求：
- 最终文件名必须使用 `coldchain-ops-plan` 作为主文件名，并保留标准电子表格工作簿扩展名。
- 结果必须保留为可见公式，跨表引用不能断。
- 请直接在当前工作目录生成输出文件，不要额外输出其他答案文件。
