读取 `/root/` 下两个输入工作簿：主体文件名分别为 `warehouse_inventory` 与 `restock_rules`，它们使用相同的 Excel 默认工作簿扩展名。使用前者中的 `Ledger` 与 `Products` 工作表，以及后者中的 `DemandPlan`、`Policy`、`Parameters` 工作表，生成新的 Excel 报表；结果文件位于 `/root/` 下，主体文件名为 `warehouse_restock_analysis`，扩展名与输入工作簿相同。

要求如下：

1. 先做标准化：
   - `Warehouse` 关联前去掉首尾空格，并统一为首字母大写形式，例如 `North Hub`。
   - `SKU` 关联前去掉首尾空格，并统一为大写。
   - `Category` 去掉首尾空格。
   - 日期按自然日计算，不要带时间部分。

2. 使用 `Parameters` 工作表中 `Parameter = AsOfDate` 的那一行作为账龄计算基准日期。

3. 以 `Ledger` 作为基准生成一个名为 `InventoryDetail` 的明细工作表，每个库存批次保留一行，不能丢行。

4. `InventoryDetail` 的列必须与下面列表完全一致，顺序也必须完全一致，不能新增或缺少任何列：
   - `BatchID`
   - `Warehouse`
   - `SKU`
   - `ItemName`
   - `Category`
   - `ReceivedDate`
   - `AsOfDate`
   - `AgeDays`
   - `AgingBucket`
   - `OnHandUnits`
   - `UnitCost`
   - `InventoryValue`
   - `WeeklyDemand`
   - `WeeksCover`
   - `TargetWeeksCover`
   - `SafetyWeeks`
   - `GapToTargetUnits`
   - `TurnoverRisk`
   - `RestockPriority`

5. 明细字段规则：
   - 先按 `SKU` 关联 `Products`，再按 `Warehouse + SKU` 关联 `DemandPlan`，再按 `Category` 关联 `Policy`。
   - `AgeDays = (AsOfDate - ReceivedDate).days`
   - `AgingBucket` 分组规则：
     - `0-30`
     - `31-60`
     - `61-90`
     - `91-180`
     - `181+`
   - `InventoryValue = OnHandUnits * UnitCost`，保留 2 位小数。
   - `WeeksCover = OnHandUnits / WeeklyDemand`；当 `WeeklyDemand == 0` 时填 `0`，保留 2 位小数。
   - `GapToTargetUnits = max(TargetWeeksCover * WeeklyDemand - OnHandUnits, 0)`。
   - `TurnoverRisk` 规则：
     - 如果 `WeeklyDemand == 0`，标记为 `Dormant`
     - 否则如果 `AgeDays > CriticalAgingDays` 且 `WeeksCover > TargetWeeksCover`，标记为 `Critical Aging`
     - 否则如果 `WeeksCover < SafetyWeeks`，标记为 `Low Cover`
     - 否则如果 `WeeksCover > TargetWeeksCover * 1.5`，标记为 `Excess Cover`
     - 其他情况标记为 `Healthy`
   - `RestockPriority` 规则：
     - 如果 `WeeklyDemand == 0`，标记为 `Monitor`
     - 否则如果 `WeeksCover < SafetyWeeks`，标记为 `Urgent`
     - 否则如果 `GapToTargetUnits > 0`，标记为 `Replenish`
     - 否则如果 `TurnoverRisk` 是 `Critical Aging` 或 `Excess Cover`，标记为 `Hold`
     - 其他情况标记为 `Normal`

6. `InventoryDetail` 需要按以下顺序排序：
   - `Warehouse` 升序
   - `RestockPriority` 按 `Urgent`、`Replenish`、`Normal`、`Hold`、`Monitor` 的顺序
   - `AgeDays` 降序
   - `BatchID` 升序

7. 在结果工作簿中额外创建以下透视表工作表：
   - `Warehouse Value`
     - Rows: `Warehouse`
     - Values: Sum of `InventoryValue`
   - `Category Aging`
     - Rows: `Category`
     - Columns: `AgingBucket`
     - Values: Sum of `OnHandUnits`
   - `Priority Gap`
     - Rows: `RestockPriority`
     - Values: Sum of `GapToTargetUnits`
   - `Warehouse Priority Matrix`
     - Rows: `Warehouse`
     - Columns: `RestockPriority`
     - Values: Sum of `InventoryValue`

8. 结果工作簿中的工作表顺序必须为：
   - `InventoryDetail`
   - `Warehouse Value`
   - `Category Aging`
   - `Priority Gap`
   - `Warehouse Priority Matrix`

最终只需要把结果保存到上文说明的 `/root/warehouse_restock_analysis` 结果工作簿文件。
