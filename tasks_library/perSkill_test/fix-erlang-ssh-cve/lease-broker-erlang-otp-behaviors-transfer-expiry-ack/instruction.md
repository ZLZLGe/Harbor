`/app/workspace/apps/lease_broker/src/lease_server.erl` 里提供了一个资源租约服务。

当前实现有一个时序问题：客户端先通过 `checkout/2` 拿到待确认租约，再用 `confirm/3` 激活；如果租约已经因为确认超时或持有超时被系统回收，邮箱里晚到的 `confirm/3` 或 `release/3` 仍然会污染资源状态，把本该空闲的资源重新写成忙碌，后续 `checkout/2` 会错误返回 `{error, unavailable}`。另外，`renew/2` 之后旧的过期定时消息也不应该再把续期后的租约提前回收。

请直接修复提供的 Erlang 代码，保证下面这些语义成立：

- `checkout/2` 成功后会占住一个待确认资源；如果在确认窗口内没有 `confirm/3`，资源必须自动回收。
- 已经过期的租约对应的 `confirm/3` 和 `release/3` 必须被忽略，不能再改写资源状态。
- 正常的 `checkout -> confirm -> renew -> release` 流程必须保持可用。
- `renew/2` 生效后，旧的超时消息不能在新租期内把资源释放掉。

只需要修改现有代码，不需要改测试，也不需要新增其他服务。
