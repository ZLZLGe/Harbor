你需要处理 `/root/data/club_cup_entries.xlsx`。

这个工作簿里有两个工作表：
1. `Club Entries`：已经填好的俱乐部杯报名与比赛成绩。
2. `Team Podium`：空白，留给你输出团队积分榜。

请把结果另存为 `/root/data/team_dots_summary.xlsx`，并满足下面要求：

1. 保留原始的 `Club Entries` 工作表。
2. 新建一个 `Athlete Dots` 工作表。
3. 从 `Club Entries` 中找出团队计分需要的列：`Club`、`LifterName`、`Sex`、`BodyweightKg`、`Best3SquatKg`、`Best3BenchKg`、`Best3DeadliftKg`。
4. 把这些列复制到 `Athlete Dots`，保留它们在 `Club Entries` 里的原列名和原相对顺序。
5. 在 `Athlete Dots` 现有列右侧追加 `TotalKg` 和 `Dots` 两列，这两列都必须使用 Excel 公式，并保留 3 位小数。
6. 按 `Dots` 从高到低排列 `Athlete Dots`。
7. 在 `Team Podium` 中输出 4 列：`Rank`、`Club`、`ScoringLifters`、`TeamDots`。
8. 每个俱乐部只统计 `Athlete Dots` 里 Dots 最高的 3 名选手；`ScoringLifters` 按这 3 名计分选手的 Dots 从高到低填写姓名，并使用英文逗号加空格连接。
9. `Team Podium` 按 `TeamDots` 从高到低排序，`Rank` 从 1 开始连续编号。

`Athlete Dots` 最终只应包含以上 9 列，`Team Podium` 最终只应包含以上 4 列。
