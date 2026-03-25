你将获得同一目标星的一条原始光变和三条候选预处理分支：

- `/root/data/raw_target.csv`
- `/root/data/pipeline_a.csv`
- `/root/data/pipeline_b.csv`
- `/root/data/pipeline_c.csv`
- `/root/data/audit_memo.txt`

所有 CSV 都包含以下列：

- `time_days`: 观测时间，单位为天
- `flux`: 归一化通量
- `flux_err`: 通量不确定度
- `quality_flag`: 质量标记，`0` 表示该曝光可用于科学分析

任务目标不是自己重新做一套去趋势，而是审计这三条候选分支，决定哪一条最适合进入后续凌星建模。正确分支应同时满足两点：

1. 明显压低原始光变中的系统噪声或残余趋势。
2. 没有把浅而重复出现的凌星信号过度抹平。

请基于原始光变与三条候选分支的对比，完成质量筛选、必要的轻量清洗、周期性下陷搜索，并把结果写入 `/root/pipeline_choice.json`。

输出必须是一个 JSON 对象，并且键必须且只包含以下四项：

- `selected_pipeline_id`
- `orbital_period_days`
- `estimated_transit_depth_ppt`
- `evidence`

字段要求如下：

1. `selected_pipeline_id` 必须是字符串，且只能是 `pipeline_a`、`pipeline_b`、`pipeline_c` 之一。
2. `orbital_period_days` 必须是数值类型，单位为天，并四舍五入到小数点后 5 位。
3. `estimated_transit_depth_ppt` 必须是数值类型，单位为 `ppt`，表示你对所选分支中浅凌星代表性深度的估计，并四舍五入到小数点后 2 位。
4. `evidence` 必须是一个长度恰好为 2 的字符串数组：
   - 第 1 条必须说明为什么所选分支同时兼顾了“压低系统噪声”和“保留浅凌星”。
   - 第 2 条必须点名至少一条未选分支，并说明它的问题是残余系统趋势过强，或过度去趋势导致浅凌星变浅 / 不稳定，或等价表述。
   - 以上两条均可使用你自己的措辞，只要判断依据表达清楚即可。

示例格式：

```json
{
  "selected_pipeline_id": "pipeline_b",
  "orbital_period_days": 6.12345,
  "estimated_transit_depth_ppt": 2.34,
  "evidence": [
    "pipeline_b 在降低系统噪声后仍保留了重复出现的浅凌星。",
    "pipeline_c 虽然更平滑，但把浅凌星压浅了，因此不适合保留。"
  ]
}
```
