你正在修复一个门店自提业务的库存预占后端服务。当前公开的 `checkout-api` 在客户端超时重试、hold 过期释放和确认下单交织时，会出现重复预占、可售库存不一致、以及已过期 hold 仍阻塞库存的问题。该服务依赖同容器内的本地 `inventory-ledger` 下游服务；你需要修复真实链路，而不是绕开它。

输入数据在：
- `/app/workspace/checkout-api/`（待修复的公开服务代码）
- `/app/workspace/docs/incident.md`（故障背景、业务约束与线上症状）
- `/app/workspace/docs/api-contract.md`（现有对外 API 契约）
- `/app/workspace/data/catalog/`（商品、门店与库存基线数据）
- `/app/workspace/data/replay/`（冻结的请求重放样本：重试、取消、确认、过期场景）
- `/services/inventory-ledger/server.py`（本地下游库存账本服务启动入口，只允许调用，不允许修改）


你的任务
1、修复 `checkout-api`，使相同 `Idempotency-Key` 的重复 hold 请求不会重复占用库存，也不会生成多个同时有效的 hold。
2、修复库存查询与状态流转行为，使 `GET /api/v1/availability`、hold 过期释放、确认下单、取消订单四条路径对 `active / expired / cancelled / confirmed` hold 的处理一致，且释放后的库存能够重新被售卖。
3、保持现有对外 API 契约兼容：不要删除现有端点、不要改变核心字段语义、不要把异步/重试语义改成另一套业务规则来规避故障。
4、保持真实运行链路可用。修复后，公开服务仍需通过现有启动方式运行，并继续通过本地 `inventory-ledger` 服务完成预占、释放和确认。
5、如果你编写了临时脚本、调试脚本或迁移脚本，最终仍需把正确修复落到正式服务代码与配置中。

输出格式：
- 原地更新 `/app/workspace/checkout-api/` 下的代码与必要配置。
- 保持以下接口继续存在并可正常工作：`POST /api/v1/holds`、`GET /api/v1/holds/{hold_id}`、`GET /api/v1/availability`、`POST /api/v1/orders/confirm`、`POST /api/v1/orders/cancel`。
- 修复后，真实链路下的业务行为必须满足题目约束与测试要求。

说明：
- 不要 hack verifier，不要根据测试文件硬编码库存数、hold 状态、订单结果或固定响应。
- 不要替换真实链路，不要绕过、短路或伪造下游 `inventory-ledger` 服务，不要把网络调用改成静态 JSON、内存假数据或本地硬写结果。
- 不要通过删功能规避问题，例如删除 hold 机制、取消幂等支持、停用过期释放、放宽确认条件、把多门店逻辑写死成单门店，或让接口直接返回空结果、固定结果。
- 不要修改隐藏下游服务、原始基线数据、测试文件或依赖配置。
- 可以自由增加日志、编写辅助分析脚本或做局部重构，但评分以正式接口在真实运行链路下的行为结果为准。
