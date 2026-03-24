请核对下面三份文件，并把有问题的付款写入 `/root/scholarship_exceptions.csv`：

- `/root/student_directory.csv`：学籍主档，包含正式姓名、常用姓名和登记收款账户。
- `/root/scholarship_awards.csv`：奖学金获奖名单，只有名单上的姓名和获奖金额。
- `/root/payout_batch.csv`：银行付款批次，包含收款人姓名、收款账户和付款金额。

你需要先把获奖名单关联到学籍主档，再把付款批次关联到获奖名单。姓名在三份文件里可能出现缩写、姓名前后倒置、连字符或撇号差异，以及轻微拼写误差。

按下面规则处理：

1. 名称标准化：
   - 全部转为小写。
   - 如果姓名里有逗号，按 `姓, 名` 处理，并改写成 `名 姓`。
   - 把连字符和撇号当作空格。
   - 删除其余标点。
   - 压缩多余空白。
2. 词级别得分：
   - 两个词完全相同得 `100`。
   - 如果其中一个词只有 1 个字母，且它等于另一个词的首字母，得 `92`。
   - 否则使用 `SequenceMatcher(None, token_a, token_b).ratio() * 100`。
3. 姓名总分：
   - 忽略词顺序。
   - 在两个姓名之间选择一组词配对，使平均词得分最高。
   - 如果两个姓名词数不同，再减去 `6 * 词数差`。
4. 先把 `scholarship_awards.csv` 的每一行匹配到 `student_directory.csv`：
   - 每个学生都可以用 `official_name` 和 `preferred_name` 两个别名参与比较，取更高分。
   - 只有当最佳学生分数 `>= 88`，且至少比第二名高 `4` 分时，才算可靠匹配。
5. 再把 `payout_batch.csv` 的每一行匹配到同一 `scholarship_code` 下的获奖名单：
   - 对每个候选获奖记录，比较 `beneficiary_name` 与该记录的 `listed_student_name`。
   - 如果这条获奖记录已经可靠匹配到某个学生，还要额外比较 `official_name` 和 `preferred_name`，三者取最高分。
   - 只有当最佳候选分数 `>= 88`，且至少比第二名高 `4` 分，并且该候选获奖记录本身已经可靠匹配到唯一学生时，才算可靠匹配。
6. 例外原因按以下顺序判定，只保留第一个命中的原因：
   - `Unmatched Student`：付款无法可靠对应到唯一且已解析的学生。
   - `Account Mismatch`：已匹配到学生，但 `destination_account` 与学籍主档 `registered_bank_account` 不一致。
   - `Amount Mismatch`：已匹配到学生，且账户一致，但 `paid_amount` 与 `approved_amount` 的绝对差值大于 `0.01`。
7. 只输出有问题的付款，保持 `payout_batch.csv` 原始顺序，CSV 列顺序必须严格为：

```text
payment_id,scholarship_code,beneficiary_name,matched_student_id,matched_student_name,destination_account,paid_amount,reason
```

如果原因是 `Unmatched Student`，则 `matched_student_id` 和 `matched_student_name` 留空。
