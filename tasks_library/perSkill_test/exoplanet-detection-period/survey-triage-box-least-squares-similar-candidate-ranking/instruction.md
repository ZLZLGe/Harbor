你在 `/root/data/survey_candidates.csv` 得到了一份已经完成基础清洗和归一化的巡天候选表。它包含 3 条光变曲线，列如下：

- `star_id`
- `time_days`
- `flux`
- `flux_err`

每个 `star_id` 对应一条独立光变曲线。你的任务是对这 3 条曲线分别做相同配置的盒状凌星周期搜索，然后从三者中选出最可信的候选体。

请使用下面这组统一搜索设置：

1. 周期搜索范围固定为 `1.5` 到 `8.0` 天。
2. 试探凌星时长固定为 `1.5` 到 `5.5` 小时之间的等间隔网格，并使用 `24` 个时长样本。
3. 搜索时将 `flux_err` 作为每个采样点的不确定度输入，并使用基于信噪比的峰值功率作为排序依据。
4. 三条曲线必须使用完全一致的搜索配置，这样 `peak_power` 才可直接比较。
5. 对每条曲线，读取其最高功率峰对应的周期、时长、深度和峰值功率。
6. 从 3 条曲线中选择 `peak_power` 最大的那一条，作为最终最可信候选体。

将结果写入 `/root/output/transit_candidate_summary.json`，并且输出 JSON 对象只能包含以下 5 个键：

- `star_id`
- `period_days`
- `duration_hours`
- `depth_ppt`
- `peak_power`

要求：

- `star_id` 必须是输入表中的某个目标编号。
- `period_days` 使用天为单位。
- `duration_hours` 使用小时为单位。
- `depth_ppt` 使用 ppt，为凌星深度的正值。
- `peak_power` 为你用于排序时采用的最高功率值。
- 所有数值字段最多保留到小数点后 5 位。

输出示例（仅示意一种合法格式）：

```json
{
  "star_id": "SVY-0000",
  "period_days": 2.34567,
  "duration_hours": 3.21000,
  "depth_ppt": 7.89012,
  "peak_power": 12.34567
}
```
