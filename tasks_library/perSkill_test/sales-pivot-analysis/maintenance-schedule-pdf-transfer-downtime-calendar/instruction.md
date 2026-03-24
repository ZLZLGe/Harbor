请读取 `/root/maintenance_notice_packet` 中的维护公告，并生成 `/root/maintenance_downtime_schedule.csv`。

这份公告包含分页排程表、重复页眉以及备注行。请提取所有计划停机窗口，并整理为标准化 CSV。

要求：

1. 合并所有页面里的排程记录，不要漏掉后续页面的时段。
2. 忽略页眉、说明文字以及所有以 `Note:` 开头的备注行。
3. 每条输出记录对应一个产线停机窗口，不要拆分或合并不同产线的记录。
4. 输出 CSV 必须只包含这 4 列，列名顺序固定为：
   - `production_line,start_time,end_time,planned_downtime_hours`
5. `production_line` 保留公告中的产线编号。
6. `start_time` 和 `end_time` 必须统一规范化为 `YYYY-MM-DD HH:MM`。
7. `planned_downtime_hours` 输出为数值，使用公告里给出的计划停机小时数。
8. 输出结果按 `start_time` 升序排序；如果开始时间相同，再按 `production_line` 升序排序。
9. 最终文件保存到 `/root/maintenance_downtime_schedule.csv`。
