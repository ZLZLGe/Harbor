# 任务说明（安全审查合规矩阵）

你需要读取安全审查发现明细，生成按组件聚合的合规矩阵 CSV。

## 输入
- 输入文件：`/app/workspace/input/review_findings.csv`
- 输入字段顺序如下：
  - `component`
  - `issue_type`
  - `severity`
  - `data_subject`
  - `has_mitigation`

## 输出
- 主输出文件：`/app/workspace/output/review_matrix.csv`
- 输出字段必须存在且顺序固定：
  - `component`
  - `critical_count`
  - `high_count`
  - `medium_count`
  - `low_count`
  - `gdpr_flag`
  - `status`

## 处理规则
1. 按 `component` 聚合同一组件的所有记录。
2. 对每个组件分别统计 `severity` 为 `critical`、`high`、`medium`、`low` 的记录数，并写入对应计数字段。
3. `gdpr_flag` 规则：
   - 若该组件任一行 `data_subject == eu_personal_data`，输出 `true`
   - 否则输出 `false`
4. `mitigation_gap` 仅用于状态判定，不写入输出：
   - 若该组件任一行 `has_mitigation == no`，则认为存在 `mitigation_gap`
   - 否则认为不存在
5. `status` 规则：
   - `fail`：`critical_count > 0`，或 `high_count >= 2`，或 `gdpr_flag == true` 且 `mitigation_gap == true`
   - `warn`：不满足 `fail` 且 (`high_count == 1` 或 `medium_count >= 2`)
   - `pass`：其他
6. 输出必须按 `component` 升序排序。
7. 所有布尔值必须使用小写字符串 `true` 或 `false`。
8. 所有计数字段必须输出为十进制整数字符串。

## 空值和禁止事项
- 不允许修改输入文件。
- 不允许联网、随机化或依赖外部服务。
- 不允许输出额外列，或改变输出字段顺序。
- 不允许输出 `null`、`None`、`nan`、`NaN`。
- 不允许把 `status` 写成 `fail`、`warn`、`pass` 之外的值。
