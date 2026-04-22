你正在修复一个 Azure Container Apps 风格的发布事故。当前 `rollout-summary-api` 的新 revision 无法稳定变为 healthy，就算偶尔能返回结果，也会退回到陈旧的本地 fallback 数据，导致值班同事看到的 rollout 摘要与真实镜像链路不一致。这个服务必须继续通过同容器内的本地控制面和隐藏下游镜像服务运行，你需要修复真实部署链路，而不是绕开它。

输入数据在：
- `/app/workspace/azure.yaml`（项目入口与部署形态说明）
- `/app/workspace/infra/containerapp.template.json`（待修复的 Azure Container Apps 风格部署模板）
- `/app/workspace/rollout-api/`（待修复的公开 API 代码）
- `/app/workspace/docs/incident.md`（故障背景、业务约束与上线症状）
- `/app/workspace/docs/deployment-contract.md`（部署约束、公开接口语义与 revision 健康要求）
- `/app/workspace/data/fallback_incidents.json`（历史 fallback 缓存，仅供排障对比，不能作为最终真实链路）
- 本地 control plane 管理面：`http://127.0.0.1:8300/__control/...`（只允许调用，不允许修改隐藏服务）
- 隐藏 mirror service：通过本地部署链路与 localhost 服务访问（只允许调用，不允许修改隐藏服务）

你的任务
1、修复 `/app/workspace/infra/containerapp.template.json`，使本地控制面能够基于现有部署模板成功发布 healthy revision，并继续保留当前的公开入口、managed identity 风格配置和 secret 引用模式。
2、修复 `/app/workspace/rollout-api/`，使公开 API 在 healthy revision 下通过真实镜像链路返回正确的 rollout 摘要和事件顺序，而不是回退到陈旧 fallback。
3、保持现有公开 API 契约兼容：不要删除现有端点，不要改掉核心查询参数或响应字段语义，不要把部署问题“改成另一套业务逻辑”来规避。
4、保持真实运行链路可用。修复后，公开 API 仍需通过本地 control plane 部署、通过隐藏 mirror service 拉取数据，并保留现有 revision 健康检查机制。
5、如果你编写了临时调试脚本、排查脚本或说明文档，最终仍需把正确修复落到正式部署模板与正式服务代码中。

输出格式：
- 原地更新 `/app/workspace/infra/containerapp.template.json` 与 `/app/workspace/rollout-api/` 下的代码和必要配置。
- 保持以下接口继续存在并可正常工作：
  - `GET /healthz`
  - `GET /api/v1/rollouts/summary`
  - `GET /api/v1/rollouts/incidents`

说明：
- 不要 hack verifier，不要根据测试文件硬编码 incident 数量、最新 incident id、snapshot id、region/service 组合或固定响应。
- 不要替换真实链路，不要绕过、短路或伪造本地 control plane 与隐藏 mirror service，不要把网络调用改成静态 JSON、纯内存假数据或只读 fallback 文件。
- 不要通过删功能规避问题，例如删掉 readiness / ingress 语义、取消 secretRef、移除 managed identity 风格头、停用 revision 健康检查，或让公开 API 永远返回空结果、固定结果。
- 不要修改隐藏服务、冻结镜像数据、测试文件或依赖配置。
- 可以自由增加日志、编写辅助分析脚本或做局部重构，但评分以正式部署模板和正式公开 API 在真实运行链路下的行为结果为准。
