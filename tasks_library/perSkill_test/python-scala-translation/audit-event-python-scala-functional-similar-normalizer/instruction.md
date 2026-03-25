# Similar: Audit Event Normalizer Translation

`/root/audit_event_normalizer.py` 是一个 Python 审计事件归一化模块。请把它翻译成一个可直接用 `scalac` 编译的 Scala 2.13 单文件实现，并将结果保存到 `/root/EventNormalizer.scala`。

输出文件必须满足这些约束：

1. 不要写 `package` 声明；验证脚本会把它当作单文件源码直接编译。
2. 只使用 Scala 2.13 标准库。
3. 需要保留并暴露这些 Scala API：
   - 类型：`EventKind`、`AuditEvent`、`NormalizedEvent`、`BaseNormalizer`、`AuditEventNormalizer`
   - 方法：`withMetadata`、`inferKind`、`normalize`、`normalizeBatch`
   - `object EventNormalizer` 中的公开函数：`makeFieldNormalizer`、`mergeMetadata`、`normalizeEvents`
4. `AuditEvent` 中的 `actor`、`resource`、`metadata` 要用能自然表达缺失值的 Scala 方式；不要退回到 `null` 风格。
5. `normalizeBatch` 和 `normalizeEvents` 必须保持惰性，按迭代方式处理批量输入，而不是先把全部结果物化。

行为契约如下，测试只会检查这些公开可观察行为：

1. `makeFieldNormalizer` 需要返回一个闭包。这个闭包会：
   - 对输入做 `trim`
   - 用小写后的文本做 alias 查找
   - 对空白或缺失值返回默认值
   - 在 alias 解析后应用传入的 `transform`
2. `mergeMetadata` 需要按“后面的 map 覆盖前面的 map”合并元数据。
3. `AuditEvent.withMetadata` 和 `NormalizedEvent.withMetadata` 需要返回合并后的新对象。
4. `AuditEventNormalizer.normalize` 需要：
   - 将缺失或空白 `actor` 归一化为 `"system"`
   - 将缺失或空白 `resource` 归一化为 `"unknown-resource"`
   - 将 `action` 归一化为：`trim` 后小写，再把空格替换成下划线
   - 将 tags 归一化为去空白、转小写、去重、按字典序输出
   - 合并 normalizer 级别 metadata 与事件自身 metadata，且事件自身值优先
5. `inferKind` 规则：
   - `login` 或 `sign_in` -> `login`
   - 以 `read_` 或 `export_` 开头，或等于 `download` / `view` -> `data_access`
   - 以 `config_` 或 `rotate_` 开头，或以 `_policy` 结尾 -> `config_change`
   - 其他情况 -> `other`

重点是写出 idiomatic Scala：用 `Option`、`Iterator`、不可变集合、模式匹配和清晰的数据建模来表达原始 Python 逻辑。
