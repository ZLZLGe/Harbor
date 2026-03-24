修复当前单模块 Java 库的 Maven 构建配置问题。

项目已经放在当前工作目录，目标输出文件是 `pom.xml`。

当前构建里用于生成描述符源码的注解处理器没有按预期参与正常编译，导致最终产物里拿不到期望的生成类。请检查 `maven-compiler-plugin` 的相关配置，修复注解处理器路径和编译参数，让生成源码重新进入正常构建流程。

要求：

1. 只修改构建配置，不要改动 `src/main/java` 下的 Java 源码。
2. 修复后，`mvn -q -DskipTests package` 应该可以成功完成。
3. 修复后，运行 `java -cp target/classes com.acme.catalog.DescriptorCli` 应输出 `id,status,total`。
