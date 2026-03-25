你在 `/root/` 会看到一个 SQLite 数据库 `district_attendance.sqlite`。库里既有目标表，也有和题目无关的辅助表。你的任务是识别“月度缺勤率持续高于自身趋势最长”的学区压力区间。

目标：

1. 读取 `district_attendance.sqlite` 中的 `monthly_absenteeism` 表，只使用以下字段：
   - `district_name`
   - `month`
   - `absenteeism_rate_pct`
2. 只保留 `2019-01` 到 `2024-12`（含）的月度数据。
3. 按 `district_name` 分组，并对每个学区：
   - 按 `month` 升序排序；
   - 直接对 `absenteeism_rate_pct` 应用 HP 滤波，平滑参数使用 `lambda = 14400`；
   - 不要做对数变换；
   - 令周期成分 `cycle = observed - trend`。
4. 对每个学区，找出 `cycle > 0` 的最长连续区间，把它视为该学区“持续高于趋势”的压力 streak。
   - 如果同一学区有多个并列最长区间，保留起始月份最早的那个。
5. 在所有学区之间比较各自的最长 streak，只保留连续月数达到全局最长的学区。
6. 生成 `absenteeism_pressure_streaks.md`，要求如下：
   - 文件必须是 UTF-8 编码的 Markdown；
   - 内容只能是一张 Markdown 表格，不要在表格前后添加说明文字；
   - 表头必须严格为：`district | streak_start | streak_end | consecutive_months`
   - 每一行对应一个入选学区；
   - `streak_start` 和 `streak_end` 使用 `YYYY-MM`；
   - `consecutive_months` 写整数；
   - 数据行按 `district` 字母顺序升序排列。

说明：

- `absenteeism_rate_pct` 本身就是率变量，本题不要取对数。
- 其他字段和其他表只是背景信息，不需要参与计算。
- 最终只需要提交 `absenteeism_pressure_streaks.md`。
