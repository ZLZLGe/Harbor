# Transfer: Python 问卷分支决策模块转 Scala

`/root/SurveyBranching.py` 是一个面向问卷分流的 Python 模块，`/root/survey_cases.toml` 提供了几组可用于自查的场景数据。请将该模块翻译成 **Scala 2.13**，并把结果保存到 `/root/SurveyBranching.scala`。

这个模块原本依赖递归遍历、可组合谓词、可空决策结果和解释路径拼装来表达问卷分支图。你的 Scala 版本需要保留等价语义，但写法应明显偏向清晰的函数式风格，而不是逐行直译。重点包括：

- 用 ADT 表达分支节点、终点节点和分支分支项。
- 用 `Option` 表达“当前还无法决策”的缺失答案状态。
- 用不可变集合和递归遍历处理整张决策图。
- 用组合函数表达 `allOf`、`anyOf` 一类条件谓词。
- 正确传播缺失答案，并构造稳定、可解释的路径说明。

为避免测试时接口不匹配，Scala 代码至少需要暴露这些公共类型与成员：

- `PredicateResult`
- `ExplanationStep`
- `DecisionResult`
- `SurveyNode`
- `OutcomeNode`
- `BranchCase`
- `BranchNode`
- `DecisionResult.isResolved(...)`
- `DecisionResult.explanationPath(...)`
- `SurveyBranching.answerEquals(...)`
- `SurveyBranching.answerIn(...)`
- `SurveyBranching.numericAtLeast(...)`
- `SurveyBranching.allOf(...)`
- `SurveyBranching.anyOf(...)`
- `SurveyBranching.evaluate(...)`
- `SurveyBranching.reachableSegments(...)`
- `SurveyBranching.renderExplanation(...)`

实现要求：

- 代码必须能被 Scala 2.13 编译。
- 输出文件只能是 `/root/SurveyBranching.scala`。
- 不要加入额外的 `package` 声明，保持文件可以被直接编译。
- 允许在不改变核心语义的前提下调整内部结构和局部命名，使实现更符合 Scala 风格。
- 不需要添加和题目无关的大量兜底逻辑。
