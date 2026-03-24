仓库位于 `/workspace`，这是一个单模块 Maven 应用，主项目在 `app/` 目录。

当前执行 `mvn -f app/pom.xml -Pproduction package` 虽然能产出 JAR，但生产 profile 需要带进去的运行时配置没有在打包前进入制品，导致产物内容不完整。问题在 `app/pom.xml` 的构建配置，不在 Java 源码。

请只修改 `app/pom.xml`，让生产 profile 下的打包结果恢复正确：执行 `mvn -f app/pom.xml -Pproduction package` 后，生成的 JAR 必须包含 `release-config/release.properties`。

不要改动 `src/` 下的源码或资源文件。最终需要提交的主要文件是 `app/pom.xml`。
