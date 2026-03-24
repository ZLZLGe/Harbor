请核对 `/root/shipping_manifest.ndjson` 与 `/root/approved_loans_catalog.tsv`，把需要人工复核的装箱清单条目逐条写入 `/root/loan_manifest_flags.ndjson`。

- `approved_loans_catalog.tsv` 是批准外借目录，提供每件作品的正式标题、借展机构和保险保单编号。
- `shipping_manifest.ndjson` 是实际装箱清单，每行一个 JSON 对象，包含箱号、清单行号、申报作品标题、借展机构和保险保单编号。

难点在于标题并不总是完全一致。装箱清单里的 `shipped_artwork_title` 可能省略副标题，也可能出现括号/标点变化、`&` 与 `and` 互换，或轻微拼写偏差。你需要先把每条箱单标题归并到唯一目录条目，再判断这条箱单是否异常。

按下面规则处理：

1. 对标题做标准化：
   - 全部转为小写。
   - 将 `&` 统一为 `and`。
   - 删除英文单引号和中文右单引号。
   - 将这些字符视为空格：`(` `)` `:` `;` `,` `.` `-`。
   - 压缩多余空白。
2. 对每个标题生成两个比较版本：
   - `full_title`：对完整标题直接做第 1 步标准化。
   - `base_title`：先删除括号内容，再按第一次出现的 `:`、`;` 或两侧带空格的连字符分割，只保留左侧主标题，再做第 1 步标准化。
3. 箱单标题与目录标题的相似度定义为以下四种比较里的最高分：
   - `full_title` 对 `full_title`
   - `full_title` 对 `base_title`
   - `base_title` 对 `full_title`
   - `base_title` 对 `base_title`
   分数计算方式为 `SequenceMatcher(None, a, b).ratio() * 100`。
4. 只有当最佳候选分数 `>= 88`，且至少比第二名高 `4` 分时，才算“可靠匹配”。
5. 如果无法可靠匹配，记为 `Unmatched Artwork`。
6. 如果可以可靠匹配，再按下面顺序检查，只保留第一个命中的原因：
   - `Borrowing Institution Mismatch`：箱单 `borrowing_institution` 与目录中的 `approved_borrowing_institution` 不一致。
   - `Insurance Policy Mismatch`：借展机构一致，但箱单 `insurance_policy_number` 与目录中的 `approved_policy_number` 不一致。
7. 只输出有问题的箱单条目，保持 `shipping_manifest.ndjson` 原始顺序。

输出必须是 NDJSON，不是 JSON 数组。每一行都必须是一个 JSON 对象，字段顺序和命名严格如下：

```json
{"manifest_line_id":"ML-003","crate_id":"CR-02","shipped_artwork_title":"Still Life with Copper Ketle","matched_catalog_id":"ART-403","matched_catalog_title":"Still Life with Copper Kettle","borrowing_institution":"Gallery of Northern Trades","insurance_policy_number":"POL-GNT-0000","reason":"Insurance Policy Mismatch"}
```

如果原因是 `Unmatched Artwork`，则 `matched_catalog_id` 和 `matched_catalog_title` 必须写成 `null`。
