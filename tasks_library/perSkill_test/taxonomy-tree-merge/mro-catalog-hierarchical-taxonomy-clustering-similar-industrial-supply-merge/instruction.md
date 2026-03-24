你要把三家工业品供应商的类目路径统一成一套 5 层 MRO 采购 taxonomy，供后续做跨供应商 spend analytics 与类目指标归一。

输入数据都在 `/root/data/`：

- `grainger_mro_catalog.csv`
  - 列：`taxonomy_path`, `commodity_group`, `sku_count`
  - 路径分隔符已经是 ` > `
- `mcmaster_mro_catalog.csv`
  - 列：`catalog_path`, `leaf_name`, `part_family`
  - 路径分隔符是 ` / `
- `fastenal_mro_catalog.csv`
  - 列：`web_hierarchy`, `terminal_node`, `branch_code`
  - 路径分隔符是 ` :: `

你的目标：

1. 读取三份输入，并把不同分隔符统一成 ` > `。
2. 标准化类目文本，尽量消除复数、连字符、`&`、大小写和近义表达差异。
3. 把语义相近的供应商类目合并到同一套 5 层采购 taxonomy 中。
4. 这套 taxonomy 要适合工业品采购分析，不要保留供应商品牌痕迹。

请遵守这些规则：

1. 输出必须是 5 层结构，顶层控制在 8-14 个 broad procurement families。
2. 类目名称使用 ` | ` 连接关键词，总词数不超过 5。
3. 子类名称不要只是父类名称的重复。
4. 同一个 unified family 下要尽量混合不同 supplier，不要按供应商拆树。
5. 语义等价的路径应尽量落到同一 `procurement_family_l1`，并尽量在 `procurement_family_l2` 继续对齐。
6. 输出中的路径列要使用统一后的 ` > ` 分隔符。
7. 不要输出供应商名、品牌名，或把原始分隔符残留到统一 taxonomy 名称里。

把结果写到 `/root/output/` 下两个文件：

1. `mro_taxonomy_mapping.csv`
   - `supplier`
   - `supplier_category_path`
   - `source_depth`
   - `normalized_leaf`
   - `procurement_family_l1`
   - `procurement_family_l2`
   - `procurement_family_l3`
   - `procurement_family_l4`
   - `procurement_family_l5`

2. `mro_taxonomy_hierarchy.csv`
   - `procurement_family_l1`
   - `procurement_family_l2`
   - `procurement_family_l3`
   - `procurement_family_l4`
   - `procurement_family_l5`

验收重点：

- 三家 supplier 的记录都要保留。
- 统一后的顶层要形成合理的 MRO 采购金字塔，而不是简单字符串改名。
- 像紧固件、劳保手套、液压软管这类跨供应商等价类目，应该能被归到同一统一 family。
