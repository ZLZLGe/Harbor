## 任务说明

`/app/workspace/arena_scoreboards/` 下有一组比赛结束后的记分牌截图。每张图都只对应 1 场已经结束的比赛，画面里有两支队伍的队名、两边的最终得分，以及一些与排名无关的数字，例如 `CLOCK`、`FOULS`、`ATTN`。

请读取该目录中的全部截图，提取每场比赛的双方队名与最终比分，并汇总生成 `/app/workspace/scoreboard_rankings.csv`。

输出文件必须是一个 CSV，且表头必须严格为：

```text
rank,team,wins,losses,points_for,points_against,net_point_diff
```

具体要求：

- 每支队伍在 CSV 中恰好出现 1 行。
- `wins` 表示该队最终得分高于对手的场次数。
- `losses` 表示该队最终得分低于对手的场次数。
- `points_for` 表示该队所有比赛的总得分。
- `points_against` 表示该队所有比赛的总失分。
- `net_point_diff` 必须等于 `points_for - points_against`。
- 行顺序必须按以下规则排序：
  1. `wins` 降序。
  2. 若 `wins` 相同，则按 `net_point_diff` 降序。
  3. 若仍相同，则按 `team` 的字母升序。
- `rank` 必须从 `1` 开始，按照最终排序结果连续编号。
- 队名保留截图中的大写形式。
- 不要输出额外列、空白行、说明行或汇总段落。

提示：

- 只统计最终比分，不要把页脚里的计时、犯规或人数等数字当成得分。
- 某些并列名次需要依赖净胜分和队名字母顺序来区分。
