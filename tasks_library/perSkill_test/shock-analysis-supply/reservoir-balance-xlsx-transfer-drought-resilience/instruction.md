你需要基于本地提供的模板工作簿与两份月度输入表，完成一个水库抗旱调度模型，并将结果保存为任务要求的主输出工作簿文件。

可用输入文件：
- 模板工作簿：包含目标工作表结构、月度骨架和预填的调度参数页。
- `monthly_hydrology.csv`：月度来水与蒸发损失。
- `water_demand.csv`：月度居民、农业与生态下泄需求。

模板中包含 5 个工作表：
- `Hydrology_Input`：导入月度来水与蒸发损失。
- `Demand_Input`：导入居民、农业与生态需求。
- `Policy`：已预填初始库容、死库容、预警阈值、限供系数、应急库容上限和年末目标库容。
- `Monthly_Balance`：需要补齐月度递推平衡和限供逻辑。
- `Scenario_Summary`：需要补齐全年摘要、季度缺水统计和运行情景判定。

请在模板基础上完成以下内容，且需要保留公式，不要把应由公式计算的结果改成手填常数：

1. 先把两份 CSV 的内容完整导入对应输入工作表，并保留原表头。

2. 在 `Monthly_Balance` 中补齐 B:V 列（第 2 行到第 13 行）：
- A 列月份已给出，也可以直接链接输入表中的月份。
- B:C 列从 `Hydrology_Input` 取回 `Inflow_MCM` 与 `Evaporation_Loss_MCM`。
- D:F 列从 `Demand_Input` 取回 `Urban_Demand_MCM`、`Agriculture_Demand_MCM`、`Eco_Min_Release_MCM`。
- G 列 `Start_Storage_MCM`：
  - 1 月等于 `Policy` 中的 `Initial_Storage_MCM`。
  - 2 月及以后等于上月 `End_Storage_MCM`。
- H 列 `Trigger_State`：
  - `Start_Storage_MCM < Emergency_Threshold_MCM` 时为 `Emergency`。
  - 否则如果 `Start_Storage_MCM < Watch_Threshold_MCM` 时为 `Watch`。
  - 否则为 `Normal`。
- I 列 `Urban_Target_MCM`：
  - `Normal` 为全部居民需求。
  - `Watch` 乘以 `Urban_Watch_Factor`。
  - `Emergency` 乘以 `Urban_Emergency_Factor`。
- J 列 `Agriculture_Target_MCM`：
  - `Normal` 为全部农业需求。
  - `Watch` 乘以 `Agriculture_Watch_Factor`。
  - `Emergency` 乘以 `Agriculture_Emergency_Factor`。
- K 列 `Emergency_Buffer_Used_MCM`：
  - 仅 `Emergency` 月份允许动用。
  - 取以下三者最小值：`Emergency_Buffer_Max_MCM`、`Planned_Release_MCM - Base_Usable_Water_MCM` 的非负部分、在不低于 `Emergency_Floor_MCM` 前提下还能额外释放的水量。
- L 列 `Planned_Release_MCM = Eco_Min_Release_MCM + Urban_Target_MCM + Agriculture_Target_MCM`。
- M 列 `Base_Usable_Water_MCM = MAX(Start_Storage_MCM + Inflow_MCM - Evaporation_Loss_MCM - Dead_Storage_MCM, 0)`。
- N 列 `Feasible_Release_MCM = MIN(Planned_Release_MCM, Base_Usable_Water_MCM + Emergency_Buffer_Used_MCM)`。
- O 列 `Eco_Actual_MCM = MIN(Eco_Min_Release_MCM, Feasible_Release_MCM)`。
- P 列 `Urban_Actual_MCM = MIN(Urban_Target_MCM, MAX(Feasible_Release_MCM - Eco_Actual_MCM, 0))`。
- Q 列 `Agriculture_Actual_MCM = MIN(Agriculture_Target_MCM, MAX(Feasible_Release_MCM - Eco_Actual_MCM - Urban_Actual_MCM, 0))`。
- R:T 列分别计算居民、农业、生态缺口：
  - `Urban_Demand_MCM - Urban_Actual_MCM`
  - `Agriculture_Demand_MCM - Agriculture_Actual_MCM`
  - `Eco_Min_Release_MCM - Eco_Actual_MCM`
- U 列 `Total_Shortage_MCM = Urban_Shortage_MCM + Agriculture_Shortage_MCM + Eco_Shortage_MCM`。
- V 列 `End_Storage_MCM = MIN(Max_Storage_MCM, Start_Storage_MCM + Inflow_MCM - Evaporation_Loss_MCM - Eco_Actual_MCM - Urban_Actual_MCM - Agriculture_Actual_MCM)`。

3. 在 `Scenario_Summary` 中补齐 B2:B21 与 E2:E5：
- B2:B8：分别汇总全年来水、居民需求、农业需求、生态目标、居民实供、农业实供、生态实供。
- B9:B11：分别计算居民服务率、农业服务率、生态达标率。
- B12：汇总全年总缺水。
- B13:B15：分别统计 `Watch` 月数、`Emergency` 月数、以及 `Emergency_Buffer_Used_MCM > 0` 的月数。
- B16：全年最低 `End_Storage_MCM`。
- B17：12 月 `End_Storage_MCM`。
- B18：`End-of-Year Storage - Target_End_Storage_MCM`。
- E2:E5：分别汇总 `Q1`、`Q2`、`Q3`、`Q4` 的 `Total_Shortage_MCM`。
- B19：`Q3` 缺水占全年总缺水的比例；若全年总缺水为 0，则返回 0。
- B20：计算 `Resilience Score = 0.45 * Urban Service Ratio + 0.25 * Agriculture Service Ratio + 0.15 * Ecological Compliance Ratio + 0.15 * (1 - Emergency Buffer Months / 12)`。
- B21：按 `Resilience Score` 判定运行情景：
  - `>= 0.82` 为 `Stable`
  - `>= 0.60` 且 `< 0.82` 为 `Managed Stress`
  - `< 0.60` 为 `Severe Stress`

输出要求：
- 最终文件名必须与任务要求的主输出文件名一致。
- 结果必须保留为可见公式，跨表链接不能断。
- 请直接在当前工作目录生成输出文件，不要额外输出其他答案文件。
