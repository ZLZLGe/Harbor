你需要基于 `/root/data/commission_source_template` 生成审计后的结算工作簿，并将结果保存到 `/root/data/`。

输入工作簿包含 4 个工作表：
- `Orders`：订单明细
- `RepRules`：销售代表基础提成规则
- `AcceleratorTiers`：季度加速档位规则
- `Payouts`：空白，等待你填写

请在 `Payouts` 中按下面顺序写入表头，并逐行对应 `Orders` 中的每一笔订单，不要遗漏、重排或汇总：

`OrderID`, `OrderDate`, `Quarter`, `RepID`, `RepName`, `Segment`, `Amount`, `BaseRate`, `QuarterRepSales`, `AcceleratorRate`, `BaseCommission`, `AcceleratorBonus`, `FinalPayout`, `AuditFlag`

填写规则如下：

1. `OrderID` 到 `Amount` 这 7 列都必须用电子表格公式从 `Orders` 引用，不能写死结果。
2. `RepName` 和 `BaseRate` 必须根据 `RepID` 从 `RepRules` 查找得到；如果找不到对应规则，这两个单元格应返回空白。
3. `QuarterRepSales` 必须用电子表格公式，计算同一个 `RepID` 在同一个 `Quarter` 下全部订单的 `Amount` 合计。
4. `AcceleratorRate` 必须根据 `QuarterRepSales` 和 `AcceleratorTiers` 计算：
   - 先按 `Quarter` 匹配对应行
   - 若季度销售额大于等于 `Tier2Min`，使用 `Tier2Rate`
   - 否则若季度销售额大于等于 `Tier1Min`，使用 `Tier1Rate`
   - 否则返回 `0`
   - 如果该季度没有加速档位规则，返回空白
5. `BaseCommission` 必须用公式计算 `Amount * BaseRate`，并保留 2 位小数；如果缺少销售代表规则，返回空白。
6. `AcceleratorBonus` 必须用公式计算 `Amount * AcceleratorRate`，并保留 2 位小数；如果缺少销售代表规则或缺少季度加速规则，返回空白。
7. `FinalPayout` 必须用公式计算 `BaseCommission + AcceleratorBonus`，并保留 2 位小数；如果任一组成部分为空白，返回空白。
8. `AuditFlag` 必须用公式输出以下结果之一：
   - `OK`
   - `MISSING_REP_RULE`
   - `MISSING_ACCELERATOR_RULE`

输出要求：
- 最终文件名必须与任务要求的主输出文件名完全一致
- 文件必须保存在 `/root/data/` 下
- `Payouts` 中从第 2 行开始的所有数据列都必须保留为电子表格公式，包括复制过来的订单字段
- 公式的缓存结果必须可直接读取，不能依赖手动打开后再重新计算
