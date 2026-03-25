你需要审查一份销售佣金结算工作簿，并输出异常 JSON 清单。

输入文件：
- `/root/commission_settlement_pack.xlsm`
  - `Orders`：订单与净签约额
  - `Rep Directory`：销售人员、佣金计划与归属区域
  - `Commission Rules`：按计划与区域配置的阶梯提成规则
  - `Advance Ledger`：每位销售在每个结算月的预支金额
  - `Manual Settlements`：人工录入的佣金结算结果

请生成 `/root/commission_exceptions.json`，输出必须是一个 JSON 数组。数组中的每个元素都表示一个异常，字段必须严格为：

- `exception_type`
- `payout_month`
- `rep_id`
- `rep_name`
- `order_id`
- `settlement_id`
- `expected_value`
- `actual_value`
- `impact_amount`

字段要求：

- `exception_type` 只能是以下五种之一：
  - `Duplicate Credit`
  - `Wrong Tier`
  - `Region Rule Mismatch`
  - `Cap Failure`
  - `Net Inconsistency`
- `order_id` 和 `settlement_id` 只允许在 `Net Inconsistency` 时为 `null`；其他异常都必须填写具体值。
- `impact_amount` 必须是数值，保留两位小数。
- 同一条人工结算记录如果同时命中多个异常，需要分别输出多条异常对象。

判定规则：

1. 先按 `(payout_month, rep_id)` 汇总 `Orders.net_bookings`，得到该销售该月的 `monthly_sales`。
2. 对每条人工结算记录，先根据 `rep_id` 找到其 `plan_code`，再根据订单的 `market_region` 和该销售该月的 `monthly_sales`，在 `Commission Rules` 中找到正确规则行：
   - 必须同时匹配 `plan_code` 与 `region_code`
   - 满足 `min_monthly_sales <= monthly_sales`
   - 且 `max_monthly_sales` 为空，或 `monthly_sales <= max_monthly_sales`
3. `Duplicate Credit`：
   - 在 `Manual Settlements` 中，若 `(payout_month, rep_id, order_id)` 重复出现，只保留该组合第一次出现的记录为基准
   - 之后再次出现的每一行都算异常
   - `expected_value` 写成 `Single settlement row for <rep_id> / <order_id> / <payout_month>`
   - `actual_value` 写成 `Duplicate of <首次出现的 settlement_id>`
   - `impact_amount` 等于该重复行的 `gross_commission`
4. `Wrong Tier`：
   - 若 `tier_used` 与正确规则的 `tier_name` 不一致，或 `rate_used` 与正确规则的 `commission_rate` 的绝对差值大于 `0.00001`
   - `expected_value` 写成 `Tier <tier_name> @ <commission_rate>`，费率保留三位小数
   - `actual_value` 写成 `Tier <tier_used> @ <rate_used>`，费率保留三位小数
   - `impact_amount` 等于 `abs(gross_commission - net_bookings * 正确费率)`
5. `Region Rule Mismatch`：
   - 若 `rule_region_used` 与订单的 `market_region` 不一致
   - `expected_value` 写成订单上的区域
   - `actual_value` 写成 `rule_region_used`
   - `impact_amount` 固定写 `0.00`
6. `Cap Failure`：
   - 若 `gross_commission - order_cap_amount > 0.01`
   - `expected_value` 写成 `Cap <order_cap_amount>`
   - `actual_value` 写成 `Gross <gross_commission>`
   - `impact_amount` 等于 `gross_commission - order_cap_amount`
7. `Net Inconsistency`：
   - 按 `(payout_month, rep_id)` 聚合 `Manual Settlements`
   - `expected_net = sum(gross_commission) - advance_amount`
   - `actual_net = sum(net_payout)`
   - 若两者绝对差值大于 `0.01`，输出一条月度异常
   - 如果 `Advance Ledger` 中没有对应记录，`advance_amount` 按 `0` 处理
   - `expected_value` 写成 `Monthly net payout <expected_net>`
   - `actual_value` 写成 `Monthly net payout <actual_net>`
   - `impact_amount` 等于两者绝对差值

输出排序要求：

- 按 `payout_month` 升序
- 再按 `rep_id` 升序
- 再按 `order_id` 升序，`null` 排最后
- 再按 `exception_type` 升序
- 再按 `settlement_id` 升序，`null` 排最后

除 `null` 之外，不要省略任何字段。
