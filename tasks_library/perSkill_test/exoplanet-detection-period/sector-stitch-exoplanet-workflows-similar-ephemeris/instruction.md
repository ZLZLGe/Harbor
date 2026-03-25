你将获得两段来自同一目标星的空间望远镜测光数据：

- `/root/data/sector_18.csv`
- `/root/data/sector_19.csv`

每个文件都包含以下列：

- `time_bkjd`: 观测时间，单位 BKJD
- `flux`: 归一化通量
- `flux_err`: 通量不确定度
- `quality_flag`: 质量标记，`0` 表示可用数据

这两段观测之间存在明显的基线偏移；每段内部还叠加了恒星活动趋势，并混入了少量耀发污染点。你的目标是把两段光变曲线拼接成同一个分析对象，完成必要的质量筛选、去趋势和凌星周期搜索，恢复该行星的星历。

请完成以下输出：

1. 在 `/root/sector_ephemeris.json` 写入一个 JSON 对象。
2. JSON 必须且只需包含下面两个键：
   - `orbital_period_days`
   - `reference_mid_transit_time_bkjd`
3. 两个值都必须是数值类型，单位分别为天和 BKJD。
4. `reference_mid_transit_time_bkjd` 定义为：在拼接后的全部观测中，最早一次可见凌星的中点时间。
5. 两个数值都四舍五入到小数点后 5 位。

示例格式：

```json
{
  "orbital_period_days": 4.12345,
  "reference_mid_transit_time_bkjd": 2201.23456
}
```

