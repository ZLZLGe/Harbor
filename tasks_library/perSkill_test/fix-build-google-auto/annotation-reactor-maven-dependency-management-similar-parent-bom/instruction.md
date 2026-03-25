修复 `/workspace/annotation-parent` 这个多模块 Maven 仓库的依赖版本管理。

当前 reactor 里与注解处理器相关的几个模块各自声明了 Guava 与 Auto 系列库的版本，已经出现漂移，导致整体构建不稳定，其中 `processor-api` 还因为拿到了过旧的 Guava 版本而无法编译。

请完成下面的结果：

1. 在父级 `/workspace/annotation-parent/pom.xml` 中集中管理下列坐标的版本，并让子模块从父级继承它们：
   - `com.google.guava:guava`
   - `com.google.auto:auto-common`
   - `com.google.auto.service:auto-service`
   - `com.google.auto.service:auto-service-annotations`
2. 子模块里凡是依赖了上述坐标的地方，都不要再显式写 `<version>`。
3. 不要改模块名，也不要移除现有模块；完成后在 `/workspace/annotation-parent` 根目录执行 `mvn test` 应该通过。

你可以修改这个仓库里的 Maven 配置文件；主要输出文件是 `/workspace/annotation-parent/pom.xml`。
