修复 `/workspace/platform-bom` 这个共享平台 POM。

这个仓库想把 Jackson、JUnit 和日志相关版本都收口到根 `pom.xml`，供两个下游模块统一使用：

- `event-service` 已经通过父 POM 继承根项目。
- `ops-cli` 已经通过导入根项目来拿版本管理。

现在根 `pom.xml` 仍把这些库写成了自己的普通依赖，导致两个下游模块虽然保留了无版本依赖声明，但 reactor 不能正确解析版本。

请只通过调整这个仓库里的 Maven 配置，完成下面的结果：

1. 让 `/workspace/platform-bom/pom.xml` 成为真正的共享版本入口：
   - Jackson 相关版本要通过根 POM 的版本管理统一提供。
   - `junit:junit`、`org.slf4j:slf4j-api` 和 `ch.qos.logback:logback-classic` 也要在根 POM 中统一管理版本。
2. 根 POM 只负责共享版本，不要把上述库继续保留为它自己的普通依赖。
3. `event-service` 与 `ops-cli` 中这些依赖声明都要继续保持无 `<version>` 写法，不要把版本重新写回下游模块。
4. 完成后，在 `/workspace/platform-bom` 目录执行 `mvn test` 应通过。

主要输出文件是 `/workspace/platform-bom/pom.xml`。
