请审计 `/root/remittance_requests.json` 中的供应商收款账户变更申请，并使用 `/root/vendor_master.csv` 作为正式供应商主档。

每条申请都包含一个 `submitted_vendor_name`。正式主档只提供 `legal_name`，两边名称可能存在缩写、后缀变化、空格/标点差异和轻微拼写误差。你需要先做名称归并，再判断申请是否有问题。

归并与判定规则如下：

1. 先对申请名称和主档名称做归一化：
   - 全部转为小写。
   - 去掉标点。
   - 压缩多余空白。
   - 将这些词视为等价并统一：
     - `inc` / `incorporated` -> `inc`
     - `corp` / `corporation` -> `corp`
     - `co` / `company` -> `co`
     - `ltd` / `limited` -> `ltd`
     - `intl` / `international` -> `intl`
     - `med` / `medical` -> `medical`
     - `svc` / `services` -> `services`
     - `mfg` / `manufacturing` -> `mfg`
     - `indl` / `industrial` -> `industrial`
     - `equip` / `equipment` -> `equipment`
2. 用归一化后的名称计算相似度。计算前先将词按字母序排序，再比较字符串相似度。
3. 只有当最佳匹配分数 `>= 90` 且领先第二名至少 `4` 分时，才算“可信匹配”。
4. 如果无法可信匹配，记为 `Unmatched Vendor`。
5. 如果可以可信匹配，再按以下顺序检查：
   - `Bank Account Conflict`: `proposed_bank_account` 与主档 `approved_bank_account` 不一致。
   - `Tax ID Conflict`: 银行账户一致，但 `proposed_tax_id` 与主档 `tax_id` 不一致。
6. 如果多个问题同时出现，只保留上面顺序更靠前的原因。

将所有有问题的申请按原始输入顺序写入 `/root/remittance_alerts.json`。只输出有问题的申请，JSON 结构必须是：

```json
[
  {
    "request_id": "RC-1002",
    "submitted_vendor_name": "Blue Harbor Indl Parts Co.",
    "matched_vendor_id": "V-2002",
    "matched_vendor_name": "Blue Harbor Industrial Parts Company",
    "proposed_bank_account": "US41BHIP000777",
    "proposed_tax_id": "11-2039485",
    "reason": "Bank Account Conflict"
  },
  {
    "request_id": "RC-1008",
    "submitted_vendor_name": "Redwood Travel Services Ltd",
    "matched_vendor_id": null,
    "matched_vendor_name": null,
    "proposed_bank_account": "US00RTS111222",
    "proposed_tax_id": "20-4455667",
    "reason": "Unmatched Vendor"
  }
]
```
