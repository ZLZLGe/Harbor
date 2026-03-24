请筛查 `/root/provider_claims.json` 中的理赔记录，并使用 `/root/authorized_clinic_registry.tsv` 作为授权医疗机构注册表。

每条理赔都有一个 `submitted_clinic_name`，但注册表只提供正式机构名 `legal_name`。两边名称可能出现缩写、标点差异、常见词形变化和轻微拼写差异。你需要先做机构名称归并，再判断这条理赔是否需要人工复核。

按下面规则处理：

1. 机构名称标准化：
   - 全部转为小写。
   - 将 `women's` 视为 `womens`。
   - 删除标点，并压缩多余空白。
   - 直接丢弃这些法律后缀词：`llc`、`pllc`、`pc`。
   - 将这些词视为等价并统一：
     - `ctr` / `center` -> `center`
     - `med` / `medical` / `medicine` -> `medicine`
     - `assoc` / `associates` -> `associates`
     - `grp` / `group` -> `group`
     - `diag` / `diagnostics` -> `diagnostics`
     - `peds` / `pediatrics` -> `pediatrics`
     - `women` / `womens` -> `womens`
   - 标准化后，将词按字母序排序，再拼回字符串。
2. 用标准化后的字符串计算相似度，得分为 `SequenceMatcher(None, a, b).ratio() * 100`。
3. 只有当最佳候选得分 `>= 88`，且至少比第二名高 `3` 分时，才算“可信匹配”。
4. 如果无法可信匹配，记为 `Unmatched Clinic`。
5. 如果可以可信匹配，再按以下顺序检查，只保留第一个命中的原因：
   - `NPI Mismatch`：理赔里的 `billed_npi` 与注册表 `authorized_npi` 不一致。
   - `State Mismatch`：`service_state` 与注册表 `state` 不一致。
   - `Settlement Account Mismatch`：`settlement_account` 与注册表 `settlement_account` 不一致。
6. 只输出有问题的理赔，保持 `/root/provider_claims.json` 原始顺序，写入 `/root/provider_claim_blocks.json`。

输出 JSON 结构必须严格为：

```json
[
  {
    "claim_id": "CLM-9002",
    "submitted_clinic_name": "Sun State Cardiology Assoc.",
    "matched_registry_id": "REG-4104",
    "matched_clinic_name": "Sunstate Cardiology Associates",
    "billed_npi": "1882754499",
    "service_state": "FL",
    "settlement_account": "SETT-SUNSTATE-09",
    "reason": "NPI Mismatch"
  },
  {
    "claim_id": "CLM-9005",
    "submitted_clinic_name": "North River Pediatric Ctr",
    "matched_registry_id": null,
    "matched_clinic_name": null,
    "billed_npi": "1548392204",
    "service_state": "OR",
    "settlement_account": "SETT-NRIVER-77",
    "reason": "Unmatched Clinic"
  }
]
```
