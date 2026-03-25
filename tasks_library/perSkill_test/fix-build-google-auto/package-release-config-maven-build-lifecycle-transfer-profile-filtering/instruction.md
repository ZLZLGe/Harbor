项目位于 `/workspace/release-bulletin-service`。

这个 Maven 项目区分 `dev` 和 `release` 两套构建配置，但当前发布构建没有把发布元数据在打包前正确处理进去。请修复构建相关配置，使下面的结果成立：

1. 在项目根目录执行 `mvn -Prelease package` 必须成功。
2. 构建结束后必须生成 `target/classes/release/build-info.properties`。
3. `target/classes/release/build-info.properties` 必须是一个过滤后的 properties 文件，至少包含这些键值：
   - `app.name=release-bulletin-service`
   - `app.version=2.7.4`
   - `deployment.environment=release`
   - `release.channel=stable`
   - `release.badge=release-2.7.4`
4. 这个文件中不能保留未替换的占位符。
5. 打出来的 JAR `target/release-bulletin-service-2.7.4.jar` 里也必须包含 `release/build-info.properties`，并且内容与 `target/classes/release/build-info.properties` 一致。

你可以修改 Maven 构建配置以及与资源过滤、profile 相关的输入文件；现有 Java 源文件不需要重写。
