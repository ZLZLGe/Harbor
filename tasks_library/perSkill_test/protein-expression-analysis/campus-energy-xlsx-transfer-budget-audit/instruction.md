请直接编辑根目录中的预算审计工作簿，保持原文件名和路径不变，不要另存为其他文件。

工作簿包含 4 个工作表：

- `BudgetAudit`：月度审计主表
- `MeterReadings`：分时电表读数台账
- `TariffTable`：月度电价表
- `BuildingInfo`：楼宇面积与预算表

你需要完成以下内容：

1. 在 `BudgetAudit!C7:O12` 补全每栋楼的审计结果。
`BudgetAudit!B2` 是本次审计月份。对 `BudgetAudit!A7:A12` 中的楼宇，按列要求填写：
- `C` 列 `Gross_Area_sqm`：按 `Building_ID` 从 `BuildingInfo` 匹配建筑面积
- `D` 列 `Monthly_Budget`：按 `Building_ID` 从 `BuildingInfo` 匹配月度预算
- `E:G` 列 `Peak_kWh`、`Flat_kWh`、`Valley_kWh`：按 `Building_ID`、`Bill_Month` 和 `Time_Band` 从 `MeterReadings` 汇总当月用电量
- `H:J` 列 `Peak_Price`、`Flat_Price`、`Valley_Price`：按 `Bill_Month` 和 `Time_Band` 从 `TariffTable` 匹配对应单价
- `K` 列 `Total_Cost`：`Peak_kWh * Peak_Price + Flat_kWh * Flat_Price + Valley_kWh * Valley_Price`
- `L` 列 `Cost_per_sqm`：`Total_Cost / Gross_Area_sqm`
- `M` 列 `Budget_Variance`：`Total_Cost - Monthly_Budget`
- `N` 列 `Variance_Pct`：`Budget_Variance / Monthly_Budget`
- `O` 列 `Status`：如果 `Budget_Variance > 0` 填 `OVER`，否则填 `WITHIN`

2. 在 `BudgetAudit!C3:G3` 完成审计概览。
- `C3`：所有楼宇 `Total_Cost` 的合计
- `E3`：`Status = OVER` 的楼宇数量
- `G3`：最大的 `Budget_Variance`

3. 在 `BudgetAudit!A18:G20` 生成超预算排行。
按 `Budget_Variance` 从高到低列出前 3 名超预算楼宇，填写：
- `Rank`
- `Building_ID`
- `Building_Name`
- `Budget_Variance`
- `Variance_Pct`
- `Total_Cost`
- `Cost_per_sqm`

额外要求：

- 目标区域请使用公式得到结果，不要手填常数
- 保留现有工作表、基本排版和已有输入数据
- 不要使用宏或 VBA
