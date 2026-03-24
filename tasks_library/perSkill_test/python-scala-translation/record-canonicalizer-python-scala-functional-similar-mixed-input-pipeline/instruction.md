# Similar: Python 记录规范化器转 Scala

`/root/RecordCanonicalizer.py` 是一个面向数据摄取流水线的 Python 模块，用来把混合类型记录规整成统一字段表示。请将它翻译成 **Scala 2.13**，并把结果保存到 `/root/RecordCanonicalizer.scala`。

你的 Scala 实现需要保持与原模块等价的核心能力，但写法应当符合 Scala 的惯用风格，而不是逐行直译。重点包括：

- 将字段种类建模成清晰的 ADT。
- 把可选元数据改写成自然的 Scala 表达。
- 用模式匹配处理异构值分发。
- 用惰性 `Iterator` 实现批量处理和文本切分。
- 用函数组合表达高阶归一化逻辑和 fluent builder。

为避免测试时出现接口不匹配，Scala 代码至少需要暴露这些公共类型与成员：

- `FieldKind`
- `CanonicalField`
- `CanonicalValue`
- `BaseCanonicalizer`
- `TextCanonicalizer`
- `NumericCanonicalizer`
- `TemporalCanonicalizer`
- `RecordCanonicalizer`
- `CanonicalizerBuilder`
- `CanonicalField.withMetadata(...)`
- `BaseCanonicalizer.canonicalizeBatch(...)`
- `RecordCanonicalizer.canonicalizeRecord(...)`
- `RecordCanonicalizer.canonicalizeRecords(...)`
- `RecordCanonicalizer.composeNormalizers(...)`
- `RecordCanonicalizer.streamTextSegments(...)`

实现要求：

- 代码必须能被 Scala 2.13 编译。
- 输出文件只能是 `/root/RecordCanonicalizer.scala`。
- 需要保留 Python 模块里的主要语义：高阶文本归一化、数字/日期/布尔/结构化值分发、可选元数据合并、记录级惰性批处理、流式文本切分。
- 允许在不改变语义的前提下调整命名与结构，使其更符合 Scala 风格。
- 不需要添加和题目无关的大量兜底逻辑。
