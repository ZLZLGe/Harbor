## 任务说明

`/app/workspace/site_photos` 下有 5 个施工区域的成对照片。每个区域都有一张 `*_before.png` 和一张 `*_after.png`，同一区域的 `area_id` 为文件名前缀。

请逐区域比较 before 和 after，只统计 **从 before 到 after 新增或恶化** 的这 4 类风险变化：

- `missing_guardrails`: before 中存在、after 中缺失的护栏段数
- `removed_warning_cones`: before 中存在、after 中缺失的警示锥数量
- `uncovered_holes`: before 中已覆盖、after 中变为未覆盖的孔洞数量
- `workers_without_helmets`: after 画面中未佩戴安全帽的作业人员数量

请把结果写入 `/app/workspace/site_safety_delta.md`，并严格使用下面的 Markdown 结构：

```md
# 施工现场安全变化报告

只统计从 before 到 after 新增或恶化的风险。

## 区域变化表
| area_id | missing_guardrails | removed_warning_cones | uncovered_holes | workers_without_helmets | risk_level |
| --- | ---: | ---: | ---: | ---: | --- |
| ... | ... | ... | ... | ... | ... |

## 总计
| metric | count |
| --- | ---: |
| missing_guardrails | ... |
| removed_warning_cones | ... |
| uncovered_holes | ... |
| workers_without_helmets | ... |

高风险区域: area_a, area_b
```

额外要求：

- `区域变化表` 中的行必须按 `area_id` 升序排列
- `risk_level` 只能使用 `stable`、`watch`、`elevated`、`critical`
- 风险分级规则如下：
  - 总变化数为 `0` 时，写 `stable`
  - 总变化数为 `1` 或 `2` 时，写 `watch`
  - 总变化数为 `3` 到 `5` 时，写 `elevated`
  - 但如果 `uncovered_holes >= 2`，或 `workers_without_helmets >= 2`，或总变化数 `>= 6`，则必须写 `critical`
- `总计` 表中的 `count` 必须是各区域对应列的求和
- `高风险区域` 只列出 `risk_level = critical` 的区域，按 `area_id` 升序，用英文逗号加空格分隔；如果没有，则写 `高风险区域: none`
- 不要输出额外章节、额外表格或额外文件
