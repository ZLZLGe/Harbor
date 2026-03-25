输入文件位于 `/root/data/loan_scoring_cases.csv`，它是一份贷款申请级别的 CSV，列为：

- `loan_id`
- `age`
- `acquisition_channel`
- `predicted_default_probability`
- `defaulted`

其中：

- `predicted_default_probability` 是模型给出的违约概率，范围在 `[0, 1]`
- `defaulted` 是真实标签，`1` 表示违约，`0` 表示未违约
- `acquisition_channel` 是获客渠道

请生成 `/root/results/loan_model_audit.md`。这是一个 Markdown 报告，必须包含下面这些一级或二级标题，标题文本要完全一致：

1. `# Loan Risk Model Audit`
2. `## Overall Metrics`
3. `## Confusion Matrix at Best Threshold`
4. `## Slice Performance by Age Band`
5. `## Slice Performance by Acquisition Channel`
6. `## Calibration Conclusions`
7. `## Audit Summary JSON`

年龄段必须按下面规则分层，并且在报告中使用这些标签：

- `18-29`：`18 <= age < 30`
- `30-44`：`30 <= age < 45`
- `45+`：`age >= 45`

`## Overall Metrics` 需要给出下面 4 个总体指标：

- `roc_auc`
- `pr_auc`
- `brier_score`
- `best_threshold`

指标口径如下：

- `roc_auc`：二分类 ROC-AUC
- `pr_auc`：正类为 `defaulted = 1` 时的 PR-AUC
- `brier_score = mean((predicted_default_probability - defaulted)^2)`
- `best_threshold`：在所有唯一 `predicted_default_probability`，并额外包含 `0` 和 `1` 作为候选阈值时，选择让 `Youden's J = TPR - FPR` 最大的阈值；如果有并列，取数值更小的阈值

`## Confusion Matrix at Best Threshold` 需要给出在 `best_threshold` 下的混淆矩阵，采用：

- 预测违约：`predicted_default_probability >= best_threshold`
- 预测未违约：`predicted_default_probability < best_threshold`

请明确写出下面 4 个计数：

- `true_negative`
- `false_positive`
- `false_negative`
- `true_positive`

`## Slice Performance by Age Band` 和 `## Slice Performance by Acquisition Channel` 都需要给出分层对比表。每一行都要包含：

- 分层名称
- `count`
- `default_rate`
- `avg_prediction`
- `calibration_gap`
- `roc_auc`
- `pr_auc`
- `brier_score`

其中：

- `default_rate = mean(defaulted)`
- `avg_prediction = mean(predicted_default_probability)`
- `calibration_gap = avg_prediction - default_rate`
- 每个分层内的 `roc_auc`、`pr_auc`、`brier_score` 只用该分层内的样本计算
- 年龄段表必须按 `18-29`、`30-44`、`45+` 的顺序输出
- 渠道表必须按 `acquisition_channel` 的字母序输出

`## Calibration Conclusions` 需要写两条结论：

- 一条针对年龄段分层
- 一条针对获客渠道分层

每条结论都要基于对应分层的 `calibration_gap`，说明：

- 哪个分层最被高估，也就是 `calibration_gap` 最大的分层
- 哪个分层最被低估，也就是 `calibration_gap` 最小的分层
- `max_abs_gap = max(abs(calibration_gap))`
- 当 `max_abs_gap > 0.05` 时，`material_issue = true`；否则为 `false`

在 `## Audit Summary JSON` 下面，必须追加一个 fenced `json` 代码块，内容是一个 JSON 对象，结构必须包含这些键：

```json
{
  "overall_metrics": {
    "roc_auc": 0.0,
    "pr_auc": 0.0,
    "brier_score": 0.0,
    "best_threshold": 0.0
  },
  "confusion_matrix_at_best_threshold": {
    "true_negative": 0,
    "false_positive": 0,
    "false_negative": 0,
    "true_positive": 0
  },
  "age_band_metrics": [
    {
      "age_band": "18-29",
      "count": 0,
      "default_rate": 0.0,
      "avg_prediction": 0.0,
      "calibration_gap": 0.0,
      "roc_auc": 0.0,
      "pr_auc": 0.0,
      "brier_score": 0.0
    }
  ],
  "channel_metrics": [
    {
      "acquisition_channel": "branch",
      "count": 0,
      "default_rate": 0.0,
      "avg_prediction": 0.0,
      "calibration_gap": 0.0,
      "roc_auc": 0.0,
      "pr_auc": 0.0,
      "brier_score": 0.0
    }
  ],
  "calibration_findings": {
    "age_band": {
      "most_over_predicted_segment": "",
      "most_under_predicted_segment": "",
      "max_abs_gap": 0.0,
      "material_issue": false
    },
    "acquisition_channel": {
      "most_over_predicted_segment": "",
      "most_under_predicted_segment": "",
      "max_abs_gap": 0.0,
      "material_issue": false
    }
  }
}
```

要求：

- JSON 中的数值必须写成 JSON number，不要写成字符串
- `material_issue` 必须写成真正的布尔值
- Markdown 正文中的结论必须和 JSON 摘要一致
- 保留足够小数，便于复核，不要粗暴四舍五入成整数
