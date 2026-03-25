你需要核验一份多页差旅报销申请文件，并只输出异常申请。

输入文件：
- `/root/expense_claims_bundle`：每页一张报销申请。
- `/root/employee_roster.csv`：员工名册，包含 `employee_id`、`employee_name` 和正确的 `payout_account`。
- `/root/trip_approvals.json`：有效出差授权，包含 `approval_code`、`employee_id` 和 `approved_city`。
- `/root/policy_limits.json`：各出行城市允许报销的金额上限。

每页申请记录至少需要提取这些字段：
- 员工姓名
- 出行城市
- 授权单号
- 报销金额
- 收款账号

按下面的优先级判断异常；一页只保留第一个命中的原因：
1. `Unknown Employee`：在 `employee_roster.csv` 中找不到该员工。匹配员工姓名时，只需要忽略大小写差异，并把连续空白折叠成一个空格后再比较。
2. `Account Mismatch`：员工存在，但申请记录中的 `payout_account` 与员工名册中的账号不一致。
3. `Invalid Approval`：授权单号为空，或者在 `trip_approvals.json` 中不存在。
4. `Employee Mismatch`：授权单存在，但它绑定的 `employee_id` 与该员工在名册中的 `employee_id` 不一致。
5. `City Mismatch`：授权单存在且员工匹配，但授权单中的 `approved_city` 与申请记录中的出行城市在忽略大小写、去掉首尾空白后仍不一致。
6. `Over Policy Limit`：以上都通过，但报销金额比 `policy_limits.json` 中该城市的上限高出超过 `0.01`。

只把异常申请写入 `/root/expense_exceptions.json`。使用 1-based 页码，并按 `expense_page_number` 升序输出。

输出必须是 JSON 数组，数组中的每个对象必须严格包含这些字段：
- `expense_page_number`
- `employee_name`
- `travel_city`
- `approval_code`
- `reimbursement_amount`
- `payout_account`
- `reason`

其中：
- `approval_code` 为空时请写成 `null`。
- `reimbursement_amount` 使用数字类型。
- `reason` 只能是上述 6 个字符串之一。

示例结构：

```json
[
  {
    "expense_page_number": 2,
    "employee_name": "Mila Stone",
    "travel_city": "Seattle",
    "approval_code": "TA-4827",
    "reimbursement_amount": 760.0,
    "payout_account": "AC-7799-08",
    "reason": "Unknown Employee"
  }
]
```
