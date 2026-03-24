请完成 `/root/data/` 目录中的赛艇积分榜工作簿。

这个工作簿包含三个工作表：
- `Results`：原始完赛记录，列为 `Athlete`、`Team`、`Event`、`EventType`、`Place`
- `ScoringRules`：积分规则，列为 `EventType`、`Place`、`Points`
- `Leaderboard`：空白工作表，等待你填写

请在 `Leaderboard` 中从 `A1` 开始建立以下列，顺序必须一致：
`Athlete`、`Team`、`Event`、`EventType`、`Place`、`Points`、`TeamTotal`、`TeamOrder`

要求：
1. 将 `Results` 中的 `Athlete`、`Team`、`Event`、`EventType`、`Place` 按原行顺序复制到 `Leaderboard`。
2. `Points` 必须使用工作簿公式，根据当前行的 `EventType` 与 `Place` 到 `ScoringRules` 中匹配积分。
3. `TeamTotal` 必须使用工作簿公式，汇总当前行所属队伍在整张 `Leaderboard` 中拿到的总积分。
4. `TeamOrder` 必须使用工作簿公式，给同一队伍内的选手做排序：积分更高者排前；若积分相同，则名次数字更小者排前；若还相同，则 `Results` 中更早出现的那一行排前。
5. 不要把计算结果手工写死；需要保留可重算的公式。
6. 保持 `Results` 与 `ScoringRules` 原样不变，并将结果保存回原文件。
