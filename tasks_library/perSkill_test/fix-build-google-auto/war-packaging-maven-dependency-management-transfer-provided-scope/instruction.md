修复 `/workspace/web-portal` 这个 WAR Web 应用的打包依赖声明。

这个项目会部署到外部 Servlet 容器中，但当前 `pom.xml` 仍把 Servlet API 当成普通编译依赖，同时共享库 `com.acme.portal:portal-bootstrap` 还把 Jetty 容器实现传递到了最终 WAR，导致产物里混入了不该随包发布的容器类。

请只通过调整 Maven 依赖声明完成下面的结果：

1. `/workspace/web-portal/pom.xml` 中 `jakarta.servlet:jakarta.servlet-api` 必须改成由部署容器提供，不再被打进 WAR。
2. `com.acme.portal:portal-bootstrap` 这条依赖需要显式排除误带入的 Jetty 容器实现，使最终 WAR 的 `WEB-INF/lib` 不再出现任何 `jetty-*.jar`。
3. 完成后，在 `/workspace/web-portal` 目录执行 `mvn package` 应成功，并生成 `target/web-portal.war`。
4. 产出的 WAR 仍需包含应用自身类和 `portal-bootstrap` 这个业务库；不要改项目坐标、打包类型或输出路径。

主要输出文件是 `/workspace/web-portal/pom.xml`。
