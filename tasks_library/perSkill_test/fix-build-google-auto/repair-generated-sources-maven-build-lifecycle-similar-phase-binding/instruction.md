项目位于 `/workspace/build-metadata-service`。

这个单模块 Maven 项目当前会在 `mvn verify` 时失败，因为 `BuildMetadata.java` 生成得太晚，编译阶段先发生了。请修复构建配置，让项目在不改坏现有业务代码含义的前提下满足下面的结果：

1. 在项目根目录执行 `mvn verify` 必须成功。
2. 构建过程中必须生成 `target/generated-sources/build-meta/com/acme/build/BuildMetadata.java`。
3. 生成出的 `BuildMetadata.java` 必须满足以下契约：
   - 包名是 `com.acme.build`
   - 声明 `public final class BuildMetadata`
   - 包含这三个常量：
     - `public static final String APP_NAME = "LedgerSync";`
     - `public static final String DEPLOYMENT_TRACK = "canary";`
     - `public static final String BUILD_REVISION = "2026.03.25";`
   - 包含 `describe()` 方法，并返回 `APP_NAME + "@" + DEPLOYMENT_TRACK + "#" + BUILD_REVISION`

你可以修改构建相关文件；现有 Java 源文件和输入属性文件不需要重写。
