你需要处理 `/root/data/meet_results.xlsx`。

这个工作簿里有两个工作表：
1. `Meet Results`：已经填好的本地公开赛成绩。
2. `Wilks`：空白，留给你生成排名表。

请完成下面的工作，并把结果另存为 `/root/data/wilks_scoreboard.xlsx`：

1. 从 `Meet Results` 中找出计算 Wilks 所需的列：`Name`、`Sex`、`BodyweightKg`、`Best3SquatKg`、`Best3BenchKg`、`Best3DeadliftKg`。
2. 把这些列复制到 `Wilks`，保留它们在 `Meet Results` 里的原列名和原相对顺序。
3. 在现有列右侧追加 `TotalKg` 和 `Wilks` 两列。
4. `TotalKg` 和 `Wilks` 都必须使用 Excel 公式，并将结果保留 3 位小数。
5. 按 `Wilks` 从高到低排列，生成可以直接查看的总排名表。
6. 输出文件必须保留原始的 `Meet Results` 工作表。

`Wilks` 工作表最终只应包含以上 8 列。
