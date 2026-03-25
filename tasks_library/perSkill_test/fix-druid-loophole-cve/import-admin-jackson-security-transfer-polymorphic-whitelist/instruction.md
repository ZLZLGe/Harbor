# 背景

`/workspace/admin-import-service` 里有一个小型 Java 管理后台导入服务，对外提供 `POST /admin/imports`。成功响应会返回导入摘要：`batchId`、`importedCount`、`importedKinds`。

当前实现把请求里的 `operations` 数组直接交给 Jackson 做多态反序列化，JSON 中的 `@class` 会决定实例化哪个实现类。代码虽然在 `readValue()` 之后只接受两种受支持的导入步骤，但这个检查发生得太晚了: 如果请求先让 Jackson 实例化了意料之外的实现类，副作用已经发生。

测试会发送一个恶意导入包，它会引用 classpath 上一个不该被管理接口接受的实现类。这个类一旦在反序列化期间被创建，就会立刻往攻击者指定的临时文件路径写入标记文件。

可参考的导入样例在 `/workspace/import-packages/`。

# 你的任务

在 `/workspace/admin-import-service` 中修复这个问题，并生成补丁文件:

- 输出补丁文件到 `/workspace/patches/0001-admin-import-type-whitelist.patch`
- 把同样的修复实际应用到 `/workspace/admin-import-service`

# 修复要求

1. 不要再让请求中的任意类名直接决定 `operations` 里每一项的具体实现。
2. 只允许目前业务支持的两种导入步骤继续通过: 主题导入和仪表盘导入。
3. 不要把所有带 `@class` 的请求一概拒绝；样例里的合法导入包仍然必须成功，成功响应里的导入摘要结构也要继续可用。
4. 恶意导入包必须在反序列化期间就被拦下，不能等对象已经实例化之后再做事后校验。
5. 补丁尽量聚焦在漏洞修复本身，不需要额外大规模重构。

# 验证重点

验证程序会检查这些可观察结果:

- 补丁文件存在且可重新应用到干净源码。
- `/workspace/admin-import-service` 里的源码已经实际修好。
- 合法的主题导入和混合导入请求继续成功，并返回导入摘要。
- 带危险实现类标记的恶意导入包会被拒绝。
- 恶意包里指定的临时文件不会被创建，说明危险实现类没有在反序列化期间被实例化。
