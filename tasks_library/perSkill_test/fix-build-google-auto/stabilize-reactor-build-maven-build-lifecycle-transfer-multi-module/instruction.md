项目位于 `/workspace/reactor-release-console`。

这是一个三模块 Maven 聚合工程，包含共享库、服务层和 CLI 三层。当前根构建配置有问题，导致 `mvn verify` 不能稳定按 reactor 关系完成整套构建，而且 CLI 模块没有在 `verify` 结束时产出可直接运行的 JAR。

请修复构建相关配置，使下面的结果成立：

1. 在项目根目录执行 `mvn verify` 必须成功。
2. 构建输出中必须能体现这三个模块都被 reactor 构建，顺序满足：
   - `shared-lib`
   - `service-layer`
   - `cli-app`
3. 构建完成后必须生成 `cli-app/target/cli-app-1.0-SNAPSHOT.jar`。
4. 这个 JAR 必须可以直接执行：运行
   `java -jar cli-app/target/cli-app-1.0-SNAPSHOT.jar`
   时，标准输出必须正好是：

```text
PLAN: nightly-ops|prepare-assets>warm-services>announce-window
```

5. 可执行 JAR 中必须包含 `com/acme/reactor/shared/ReleaseCatalog.class`、`com/acme/reactor/service/RolloutPlanner.class` 和 `com/acme/reactor/cli/ReleaseCli.class`。

你可以修改 Maven 构建配置以及与模块构建相关的 POM 文件；现有 Java 源文件不需要重写。
