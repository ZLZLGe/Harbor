`/app/workspace` 里是一套 Rust 写的 SSH 隧道代理。

当前 remote forwarding ACL 过于宽松：远程端口转发请求会把 `0.0.0.0`、`::`、`*` 这类公开绑定和未授权的目标端口当成可接受，外部用户可以借此把 bastion 上的本地服务经 `-R` 暴露出去。你需要先确认是哪类 bind/target 组合被错误放行，再收紧 ACL。

修复后需要同时满足：

- 远程转发只允许策略白名单中的 loopback 绑定与 loopback 目标
- 只有白名单中的目标端口可以被转发，未授权端口必须拒绝
- 测试里保留的运维隧道（IPv4 与 IPv6 loopback）仍然可用

把主要修改放在 `/app/workspace/src/forwarding/remote_acl.rs`，只修改提供的代码并让测试通过即可。
