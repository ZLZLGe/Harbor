你需要处理 `/root/data/bench_nationals_results.csv`，并生成 `/root/data/bench_goodlift_ranking.csv`。

输入文件是一份卧推专项全国赛成绩表，每行都代表一名选手的正式成绩记录。请按 IPF Goodlift 规则计算分数，并输出一份可直接发布的排名 CSV。

要求如下：

1. 本题是卧推专项，`Best3BenchKg` 就是用于计算 Goodlift 的 lifted total，不要把它当成三项总成绩。
2. 根据每行的 `Sex`、`Equipment` 和 `Event` 选择正确的 Goodlift 分支；数据里会同时出现 `Raw` 和 `Single-ply`。
3. 体重低于 `35kg` 的记录，`Goodlift` 记为 `0.00`。
4. 输出文件必须只包含以下列，且顺序固定为：
   `OverallRank`、`ClassRank`、`ScoringClass`、`LifterName`、`Province`、`Sex`、`Equipment`、`Event`、`BodyweightKg`、`Best3BenchKg`、`Goodlift`
5. `ScoringClass` 的格式为 `Sex|Equipment|Event`，例如 `F|Raw|B`。
6. `Goodlift` 保留 2 位小数，并以两位小数的文本形式写入 CSV。
7. 先按 `Goodlift` 从高到低排序；如果分数相同，再按 `Best3BenchKg` 从高到低排序；如果仍然相同，再按 `LifterName` 的字母顺序升序排序。
8. `OverallRank` 按最终总排名从 `1` 开始连续编号。
9. `ClassRank` 只在相同 `ScoringClass` 内排名，排序规则与总排名相同，并且每个 `ScoringClass` 内都从 `1` 开始重新编号。

除上述 11 列外，不要输出其他列。
