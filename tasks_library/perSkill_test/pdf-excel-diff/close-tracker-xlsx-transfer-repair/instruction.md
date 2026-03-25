你在协助财务团队修复一个月结跟踪模板。

输入文件：
- 位于 `/root/` 下、文件名前缀为 `close_tracker_template` 的模板工作簿

这个模板最近被插入了新列，导致多个公式引用错位。请在不改变原有工作表数量、顺序和版式的前提下，修复模板并输出：

- 位于 `/root/` 下、文件名前缀为 `close_tracker_repaired` 的修复后工作簿

输出工作簿必须保留且仅保留以下 3 个工作表，顺序不变：

1. `Close Tracker`
2. `Owner Map`
3. `Dashboard`

`Close Tracker`
- 保留第 4 到 8 行、A 到 F 列现有的手工数据不变。
- G 列 `status` 必须是公式单元格，规则如下：
  - `actual_day` 为空时显示 `Open`
  - `actual_day <= planned_day` 时显示 `On Time`
  - 其余情况显示 `Late`
- H 列 `delay_days` 必须是公式单元格，规则如下：
  - `actual_day` 为空时保持空白
  - 否则返回 `MAX(actual_day - planned_day, 0)`
- I 列 `owner_email` 必须是公式单元格，根据 `owner_id` 从 `Owner Map` 取回邮箱地址。
- J 列 `escalation` 必须是公式单元格：
  - 当 `status = "Late"` 且 `delay_days >= 2` 时显示 `Escalate`
  - 其余情况保持空白

`Dashboard`
- 保留 A2:A8 现有指标名称不变，B2:B8 都必须是公式单元格。
- 这些指标分别表示：
  - `B2`: 跟踪项总数
  - `B3`: `Late` 的数量
  - `B4`: `On Time` 的数量
  - `B5`: `Open` 的数量
  - `B6`: `Escalate` 的数量
  - `B7`: 最大 `delay_days`
  - `B8`: 仅对大于 0 的 `delay_days` 求平均值

通用要求：
- 除修复公式和值缓存外，不要改动现有的工作表名称、顺序、合并单元格、冻结窗格、列宽、行高、标题/表头样式，或 `Owner Map` 里的查找表内容。
- `Close Tracker` 的 G:J 和 `Dashboard` 的 B2:B8 在输出中都必须仍然是公式单元格，不能把最终结果直接写死。
- 保存后的工作簿中不能出现 `#REF!`、`#DIV/0!`、`#VALUE!`、`#NAME?`、`#N/A` 等可见公式错误。
