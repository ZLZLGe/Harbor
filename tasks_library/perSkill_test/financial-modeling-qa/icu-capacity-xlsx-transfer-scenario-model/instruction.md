请修复位于 `/root/icu_capacity_template` 的模板工作簿，并将完成后的模型保存到 `/root/ward_capacity_model`。

这两个路径都是环境里已准备好的工作簿别名。请保留现有 3 个工作表及其名称：

- `Assumptions`
- `Ward Load`
- `Staffing Summary`

当前模板里，黄色结果区存在缺失或断开的公式，`Staffing Summary` 也没有随着前两张表联动。请在保留现有标题、布局和输入数值的前提下完成下面内容：

1. `Ward Load!F6:H10` 必须按各 scenario 计算 projected census，逻辑为：
   `MIN(staffed beds, ROUND(local census * local occupancy multiplier + transfer share * transfer add-on patients, 0))`
2. `Ward Load!I6:K10` 必须计算各 scenario occupancy，即：
   `projected census / staffed beds`
3. `Staffing Summary!B5:D14` 必须全部改成公式，并且只能引用工作簿内已有输入或中间结果，不能手工填最终数字。
4. `Staffing Summary` 各行含义如下：
   - row 5: total projected census = 同一 scenario 下 `Ward Load` 中 5 个病区 projected census 之和
   - row 6: available staffed beds = `SUM(Ward Load!C6:C10) - row 5`
   - row 7: required RN per shift = `ROUNDUP(total census / RN patients per nurse / shift, 0) + float nurse coverage / shift`
   - row 8: required RT per shift = `ROUNDUP(total census / RT patients / therapist / shift, 0)`
   - row 9: required intensivists per day = `ROUNDUP(total census / Intensivist patients / physician / day, 0)`
   - row 10: effective RN per shift incl. absenteeism = `ROUNDUP(row 7 * (1 + absenteeism uplift), 0)`
   - row 11: effective RT per shift incl. absenteeism = `ROUNDUP(row 8 * (1 + absenteeism uplift), 0)`
   - row 12: effective intensivists per day incl. absenteeism = `ROUNDUP(row 9 * (1 + absenteeism uplift), 0)`
   - row 13: max unit occupancy
   - row 14: units above 90% occupancy，按严格大于 `90%` 统计
5. `Ward Load!F6:K10` 和 `Staffing Summary!B5:D14` 都必须由公式驱动，而不是静态硬编码。
6. 成品必须仍然是可直接审阅的工作簿，不要额外输出其他文件。
