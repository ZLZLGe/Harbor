# Similar: Message Canonicalizer Translation

`/root/MessageCanonicalizer.py` 是一个 Python 消息规范化模块。请将它改写为 **Scala 2.13**，并把最终代码保存到 `/root/MessageCanonicalizer.scala`。

目标不是逐行直译，而是在保持行为一致的前提下，把 API 改成更符合 Scala 习惯的设计。你的 Scala 代码至少需要提供这些组件：

- `MessageLike`
- `MessageProcessor`
- `MessageKind`
- `CanonicalMessage`
- `BaseCanonicalizer`
- `TextCanonicalizer`
- `MetricCanonicalizer`
- `StructuredCanonicalizer`
- `MessagePipeline`
- `MessageCanonicalizer` 对象，并在其中暴露 `canonicalizeMessage`、`canonicalizeBatch`、`summarizeByKind`

请满足这些要求：

- 使用 case class、sealed hierarchy、`Option`、不可变集合和表达式风格。
- 不要把 Python 里的可变默认值、鸭子类型和链式原地修改直接搬到 Scala 中。
- 文本消息需要做去首尾空白、压缩连续空白；默认文本规范化结果为小写。
- 字节消息按 UTF-8 解码。
- 指标消息要保留可配置精度并按 `HALF_UP` 规则四舍五入，同时记录原始数值类型。
- 结构化消息要稳定排序字段，忽略缺失字段，规范化 `channel` / `tags`，并把时间格式化成 `yyyy-MM-ddTHH:mm:ss`。
- `MessagePipeline` 需要按顺序应用处理器，并支持批量规范化。
- 代码必须能通过 Scala 2.13 编译，并通过测试直接运行。

除了通过测试，也请让代码本身保持清晰、可读、易维护。
