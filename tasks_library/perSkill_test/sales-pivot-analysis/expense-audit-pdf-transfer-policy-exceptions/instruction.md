请读取 `/root/expense_review_packet`，并生成 `/root/expense_policy_exceptions.json`。

这份审计资料里包含两类表格：
- 报销类别上限表
- 员工报销明细表

要求：

1. 从整份资料中提取所有相关表格，不要漏掉后续页面的明细。
2. 先读取报销类别上限表，建立 `category -> limit_amount` 的映射。
3. 再把员工报销明细按 `employee_id + employee_name + category` 合并，计算每个员工在每个类别下的 `claimed_amount` 总额。
4. 只保留 `claimed_amount` 严格大于该类别 `limit_amount` 的异常记录。
5. 每条异常输出为一个 JSON 对象，字段固定为：
   - `employee_id`
   - `employee_name`
   - `category`
   - `claimed_amount`
   - `limit_amount`
   - `exception_reason`
6. `exception_reason` 只能使用下面两个值之一：
   - `single claim exceeds category cap`
   - `combined claims exceed category cap`
7. 如果某个员工在某个类别中有任意单笔申报金额已经大于上限，`exception_reason` 必须为 `single claim exceeds category cap`。
8. 否则，只要该员工该类别的合计金额超限，`exception_reason` 必须为 `combined claims exceed category cap`。
9. `claimed_amount` 和 `limit_amount` 必须输出为整数。
10. 最终 JSON 必须是一个数组，并按 `employee_id` 升序、再按 `category` 升序排序。

最终文件保存到 `/root/expense_policy_exceptions.json`。
