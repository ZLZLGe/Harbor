修复 `/workspace/grpc-gateway` 这个单模块 gRPC 网关工程的依赖版本对齐。

仓库已经把 proto 编译产物提交到了 `src/generated-sources`。最近 proto 编译链升级后，这些生成代码开始引用较新的 `io.grpc` 注解和 `com.google.protobuf` 运行时校验 API，但根 `pom.xml` 仍把几组 `grpc-*` 与 `protobuf-*` 依赖写成了漂移的显式版本；另外，`com.google.api.grpc:proto-google-common-protos` 还会把旧的 protobuf runtime 传递进来。

请只通过调整这个仓库里的 Maven 配置，完成下面的结果：

1. 让 `/workspace/grpc-gateway/pom.xml` 成为 gRPC 与 Protobuf 版本的单一入口：
   - `grpc-netty-shaded`、`grpc-protobuf`、`grpc-stub` 要从统一的版本管理里取版本。
   - `protobuf-java` 与 `protobuf-java-util` 也要从统一的版本管理里取版本。
   - 上述依赖在普通 `<dependencies>` 里不要再继续写 `<version>`。
2. `com.google.api.grpc:proto-google-common-protos` 这条依赖必须保留，但需要显式排除它带入的 `protobuf-java` 和 `protobuf-java-util`，避免和你统一管理的 runtime 混用。
3. 不要改项目坐标、源码目录或测试代码。完成后，在 `/workspace/grpc-gateway` 目录执行 `mvn test` 应通过。

主要输出文件是 `/workspace/grpc-gateway/pom.xml`。
