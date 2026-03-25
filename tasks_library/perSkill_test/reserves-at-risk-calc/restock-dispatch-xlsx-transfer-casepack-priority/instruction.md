请在输入工作簿 `/root/data/restock_planner.x` + `lsx` 上完成补货派发模型，并将结果另存为输出工作簿 `/root/output/restock_dispatch_board.x` + `lsx`。

所有新增计算都必须保留为工作表公式。`Dispatch Board` 中除优先级序号外，其余输出列都应链接 `Restock Plan`，不要把最终结果手填成常数。

1. 在 `Restock Plan` 表第 2-11 行补全每个门店-SKU 的计算。
   - `A:B` 按 `Demand` 表相同行链接 `Store` 与 `SKU`，顺序保持与 `Demand` 表一致。
   - `C:D` 分别链接 `Demand` 表中的 `Avg Daily Demand` 与 `Target Cover Days`。
   - `E` 从 `On Hand` 表取回对应门店-SKU 的 `Units On Hand`。
   - `F` 从 `Lead Times` 表取回该门店的 `Lead Time Days`。
   - `G` 计算到货前可到达的在途量：仅汇总 `Inbound` 表中 `ETA Day <= Lead Time Days` 的同门店-SKU `Inbound Qty`。
   - `H` 计算该门店-SKU 的全部在途量。
   - `I` 计算到货前缺口：`MAX(Avg Daily Demand * Lead Time Days - On Hand Units - Inbound Before Arrival, 0)`。
   - `J` 计算补货目标缺口：`MAX(Avg Daily Demand * (Target Cover Days + Lead Time Days) - On Hand Units - Total Inbound, 0)`。
   - `K` 从 `Case Packs` 表取回该 SKU 的 `Case Pack Qty`。
   - `L` 计算建议下单量：若 `J=0` 则写 `0`，否则按 `Case Pack Qty` 向上取整。
   - `M` 计算补货后覆盖天数：`(On Hand Units + Total Inbound + Suggested Order Qty) / Avg Daily Demand - Lead Time Days`。
   - `N` 计算优先级分数：`Gap Before Arrival * 100 + MAX(Target Cover Days - Post-Restock Coverage Days, 0)`。
   - `O` 输出缺货预警：若 `Gap Before Arrival >= Avg Daily Demand * 2` 则写 `CRITICAL`；若 `Gap Before Arrival > 0` 则写 `WATCH`；否则写 `OK`。

2. 在 `Dispatch Board` 表第 2-11 行输出派发优先级。
   - 将全部 10 个门店-SKU 组合按 `Restock Plan` 的 `Urgency Score` 降序排序。
   - 若优先级分数相同，再按 `Gap Before Arrival` 降序排序；若仍相同，再按 `Store` 升序、`SKU` 升序排序。
   - `A` 列填写优先级序号 `1-10`。
   - `B:H` 依次链接排序后组合的 `Store`、`SKU`、`Gap Before Arrival`、`Suggested Order Qty`、`Post-Restock Coverage Days`、`Stockout Warning`、`Urgency Score`。

3. 保持现有工作表名称不变，输出文件路径必须是 `/root/output/restock_dispatch_board.x` + `lsx`。
