# Transfer: 评分量表模块翻译

`/root/RubricScorer.py` 是一个 Python 评分量表模块，`/root/rubric_submissions.csv` 提供了批量评分时会用到的示例答卷。请把该模块翻译为 Scala 2.13，并将结果保存到 `/root/RubricScorer.scala`。

要求：

- Scala 文件必须使用 `package rubric`。
- 需要保留并实现这些核心类型：`RubricQuestion`、`ScoreResult`、`SubmissionReport`、`AbstractScorer`、`TextRubricScorer`、`NumericRubricScorer`、`WeightedRubricScorer`、`BatchRubricScorer`。
- 需要保留并实现这些核心接口或方法：`fromPayload`、`fromEvaluation`、`withMetadata`、`scoreRaw`、`buildResult`、`score`、`scoreSubmission`、`scoreAll`、`averageRatio`、`render`。
- 语义应与 Python 版本一致：题目载荷解析、不可变评分结果、文本/数值/加权评分逻辑、批量评分顺序、汇总比率计算，以及结果元数据合并行为都要保持一致。
- 只依赖 Scala 2.13 标准库，不要引入第三方库。
- 代码应符合 Scala 风格，不要做逐行机械翻译。
