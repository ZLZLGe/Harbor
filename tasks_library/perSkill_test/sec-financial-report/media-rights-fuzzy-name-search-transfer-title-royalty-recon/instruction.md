你在一家做 13F 复核的研究运营团队工作。本题需要直接使用当前环境里提供的名称模糊检索工具；它已经能对基金管理人名称和股票发行人名称做模糊检索。

输入文件已经放在：

- `/root/2025-q2/COVERPAGE.tsv`
- `/root/2025-q2/INFOTABLE.tsv`

请完成下面的任务，并把最终结果写入 `/root/royalty_reconciliation.json`：

1. 基金管理人定位
   使用当前环境提供的名称模糊检索工具，在 `2025-q2/COVERPAGE.tsv` 中定位下面 2 个不规范基金名称对应的标准 13F filing：
   - `bridge water assoc`
   - `renaissance tech llc`

2. 发行人定位
   使用当前环境提供的名称模糊检索工具，在 `2025-q2/INFOTABLE.tsv` 中定位下面 3 个不规范发行人名称对应的标准 `CUSIP`：
   - `palantir tech`
   - `nvidia corp`
   - `micro strat`

3. 持仓筛选
   在 `INFOTABLE.tsv` 中，只保留同时满足下面两个条件的持仓行：
   - `ACCESSION_NUMBER` 属于第 1 步匹配出的目标基金
   - `CUSIP` 属于第 2 步匹配出的目标发行人

4. 管理人敞口汇总
   按 `ACCESSION_NUMBER` 聚合第 3 步保留的持仓，输出所有目标基金的：
   - `total_value_usd`
   - `total_shares`
   - `matched_cusips`：该管理人在目标发行人范围内持有过的标准 `CUSIP` 列表

   排序规则：
   - 先按 `total_value_usd` 降序
   - 如有并列，再按 `ACCESSION_NUMBER` 升序

5. 重复持仓分组
   对第 3 步保留的持仓，如果 `(ACCESSION_NUMBER, CUSIP)` 组合出现次数大于 1，就视为重复持仓分组。

6. 最大单笔持仓
   在第 3 步保留的持仓里，找出 `VALUE_USD` 最大的单笔持仓。
   如果有并列，依次按 `ACCESSION_NUMBER`、`CUSIP`、`POSITION_ID` 升序取第一条。

7. 输出格式
   输出 JSON 必须严格符合下面的 schema：

```json
{
  "fund_matches": [
    {
      "search_term": "string",
      "accession_number": "string",
      "filingmanager_name": "string",
      "form13f_file_number": "string"
    }
  ],
  "issuer_matches": [
    {
      "search_term": "string",
      "cusip": "string",
      "issuer_name": "string"
    }
  ],
  "selected_position_summary": {
    "matched_fund_count": 0,
    "matched_issuer_count": 0,
    "selected_position_rows": 0,
    "total_value_usd": 0.0
  },
  "manager_exposure_rank": [
    {
      "rank": 1,
      "accession_number": "string",
      "filingmanager_name": "string",
      "total_value_usd": 0.0,
      "total_shares": 0,
      "matched_cusips": ["string"]
    }
  ],
  "duplicate_position_groups": [
    {
      "accession_number": "string",
      "filingmanager_name": "string",
      "cusip": "string",
      "issuer_name": "string",
      "position_ids": ["string"],
      "duplicate_count": 0
    }
  ],
  "largest_position": {
    "position_id": "string",
    "accession_number": "string",
    "filingmanager_name": "string",
    "cusip": "string",
    "issuer_name": "string",
    "value_usd": 0.0,
    "shares": 0
  }
}
```

额外要求：

- `fund_matches` 必须按给定搜索词顺序输出。
- `issuer_matches` 必须按给定搜索词顺序输出。
- `manager_exposure_rank` 必须给出连续的 `rank`。
- `matched_cusips` 和 `position_ids` 都必须按升序输出。
- `duplicate_position_groups` 必须按 `ACCESSION_NUMBER`、`CUSIP` 升序输出。
- 所有金额字段都输出数字，不要输出字符串。
