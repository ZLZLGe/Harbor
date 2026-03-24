修复当前发布文档模块的 Maven 构建配置问题。

项目已经放在当前工作目录，目标输出文件是 `docs/pom.xml`。

当前 `docs` 模块在发布构建里需要附带 API 文档制品，但现在在当前 JDK 下执行 `mvn -q -pl docs -am package` 时，生成文档这一步会失败，导致 `release-docs-1.0.0-SNAPSHOT-javadoc.jar` 无法稳定产出。请检查 `docs/pom.xml` 里负责生成 API 文档制品的构建配置，修复当前 JDK 下的源码级别与文档生成设置，让默认发布流程重新附带 javadoc jar。

要求：

1. 只修改构建配置，不要改动 `docs/src/main/java` 下的 Java 源码。
2. 修复后，`mvn -q -pl docs -am package` 应该可以成功完成。
3. 修复后，`docs/target/release-docs-1.0.0-SNAPSHOT-javadoc.jar` 应存在，并包含 `com/acme/release/docs/ReleaseChannelGuide.html` 页面。
