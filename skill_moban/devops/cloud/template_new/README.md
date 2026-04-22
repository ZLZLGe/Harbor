# Cloud 模板任务说明

本模板面向 `cloud` 类任务，重点对齐 SkillsMP cloud 分类里当前高相关、且高信号的 `azure-deployment-preflight`、`cloud-architect`、Azure Container Apps / containerization 一类 deployment skills。模板目标不是让 solver 从零搭一个云系统，而是把 solver 放进一个真实风格的云发布事故现场：有 IaC 风格部署模板、有本地 control plane、有真实的公开服务进程、有隐藏下游镜像链路，还有必须一起成立的 deploy health 与行为结果。

## 模板范式

1. 任务必须落在真实云运维/云部署工作流里，优先做模板预检、revision 健康检查、secret / identity 绑定、流量接入、下游访问和镜像一致性这类真实问题，不做靠隐藏答案文件取巧的 puzzle。
2. `instruction.md` 只能给症状、业务约束和禁止事项，不能直接泄漏根因或指导修复步骤。
3. 环境必须保留真实风格的上下游依赖。对 cloud 任务，至少要有公开服务、同容器本地控制面、以及真实 localhost 下游链路，不能退化成纯静态 JSON 题。
4. Verifier 只验行为结果，不绑定唯一实现。只要 healthy revision、公开 API 契约和真实链路行为满足要求，就应允许不同修复路径通过。
5. Hidden-style guardrails 要优先卡“仍在真实部署链路中运行”而不是只卡表层 JSON。例如本模板额外要求 public API 请求必须继续命中隐藏镜像服务并留下审计事件。
6. Guardrails 要能拦截 cloud 任务里的常见伪修复：硬编码 snapshot、绕过 control plane、去掉 secretRef/identity 机制、直接读 fallback 文件、改动隐藏镜像数据或隐藏服务。
7. 正式 with_skill / without_skill 对照里，唯一区别只能来自 `environment/skills/` 及对应 Dockerfile 复制逻辑，不能额外改题面、测试、数据或依赖。
8. Skill 的验收标准应是“标准化预检与运行态诊断路径，并显著提高通过率或收敛稳定性”，而不是只让任务快一点。

## 示例任务

## 📌 任务元数据

- 任务名：`azure-container-apps-rollout-preflight-repair`
- 类别：`cloud`
- 难度：`hard`
- 标签：`cloud`, `azure`, `containerapps`, `deployment`, `preflight`, `managed-identity`, `fastapi`
- 绑定 Skill：`azure-deployment-preflight`

任务要求修复一个 Azure Container Apps 风格的 rollout summary 服务。Solver 需要在保留真实 localhost control plane 与隐藏 mirror service 的前提下，修复部署模板和 API 服务代码，使 revision 变为 healthy，并让公开接口继续通过真实镜像链路返回正确的 snapshot 与 incident 排序。

环境是单容器实现，包含三部分：

- `workspace/`：待修复的 `azure.yaml`、部署模板、公开 API 代码、故障说明与 fallback 对比数据。
- `control-plane/`：本地 Azure Container Apps 风格控制面与 ingress 代理。
- `mirror-service/`：真实下游镜像服务与冻结 incident snapshot。
- `skills/azure-deployment-preflight/`：标准化 preflight、revision 检查和镜像审计脚本。

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- 测试用例：`10/10` 通过
- 有效样本：`cloud-template-new-oracle-20260421j / cloud_template_new_oracle_202604__pPVeBep`

Verifier 策略：

- 主测：healthy revision、`summary` 结果正确性、`incidents` newest-first 顺序、redeploy 后的真实镜像链路稳定性，以及 storage / servicebus / redis 这些隐藏组合的 summary 契约。
- 防作弊：拦截篡改隐藏 control plane、修改隐藏镜像数据、用 fallback 替代真实链路、删除 readiness / secretRef / managed identity 风格配置，或把公开请求从真实 mirror audit 上移开。

数据质量：

- 镜像数据采用冻结的 Azure Service Health 风格 incident snapshot，字段包含 `tracking_id`、`service_slug`、`region`、`severity`、`status`、`opened_at`、`updated_at` 等真实风格结构，并额外包含仅用于真实 summary 投影的 `summary_eligible` 信号。
- 部署模板采用 Azure Container Apps 风格 JSON，而不是自造 key-value 题面。
- 运行时同时覆盖静态模板问题、revision 健康问题与真实下游鉴权问题；solver 只能通过 localhost 调用隐藏服务，不能直接读取隐藏服务源码或冻结快照。

数据来源：

- 字段风格与事故类型参考 Microsoft Azure Service Health / Azure Status 的公开事故表达。
- 任务内使用的是仓内冻结快照，不在评测时在线抓取，以保证确定性与可测性。

多模态：

- 不适用（纯部署 / API 运行时任务）。

## ⚡ Skill 相关性评估

结论：强相关，但价值主要体现在正确性覆盖，而不是单纯省时或省 token。

这个任务里，Skill 的核心价值不是直接替 solver 修改模板或代码，而是把最容易走弯路的诊断流程标准化：

- 先跑模板预检，优先找到阻塞 revision 的 target port / secretRef 等静态问题。
- 再触发真实 apply，并检查 revision 事件与 health，而不是只盯着公开 API 的 503。
- 然后校验 public summary 的 `snapshot_id`、`latest_incident_id` 和排序结果。
- 最后核对 mirror audit，确认结果来自真实镜像链路，而不是 fallback。

没有 skill 时，任务理论上仍可解，但 solver 需要自己拼出 control-plane 调试路径、mirror 审计口径以及“模板问题和应用问题同时存在”的收敛顺序，诊断与定位成本明显更高。

这个任务里最隐蔽、最容易漏掉的点，不是 template preflight 本身，而是 `storage` / `redis` 这两组 summary 需要额外经过 `summary_eligible` 投影；无 skill solver 很容易只修到 healthy revision、真实镜像链路和排序，却漏掉这层 contract。Skill 的 `contract matrix + mirror audit` 正是在这里拉开差距。

基于最近 `3` 次有效对比实验：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` (`0%`) | `2/3` (`66.7%`) | With Skill 出现可复现通过样本；Without Skill 连续 3 次均未通过 |
| 总耗时 | `387.3s` | `395.9s` | 总耗时接近，With Skill 略慢约 `2.2%`，说明 skill 价值主要不在省时 |
| Agent 执行耗时 | `299.0s` | `295.0s` | With Skill 略快约 `1.4%`，收敛速度接近但更稳定 |
| Input Tokens | `665,464.7` | `808,975.3` | With Skill token 更高约 `1.22x`，主要来自 contract matrix 与 mirror audit 的覆盖式验证 |

最近 3 次有效样本：

- With Skill：
  `cloud-template-new-with-skills-e2b-20260421j` -> `1.0`
  `cloud-template-new-with-skills-e2b-20260421m` -> `1.0`
  `cloud-template-new-with-skills-e2b-20260421n` -> `0.0`
- Without Skill：
  `cloud-template-new-without-skills-e2b-20260421k` -> `0.0`
  `cloud-template-new-without-skills-e2b-20260421m` -> `0.0`
  `cloud-template-new-without-skills-e2b-20260421n` -> `0.0`

失败轨迹摘要：

- Without Skill 的 3 次失败都修到了 healthy revision 和真实链路，但至少漏掉了一部分summary 投影；典型失败是 `storage` / `redis` 仍把 `summary_eligible=false` 的事件算进 summary，或保留了错误的 `servicebus` 特判。
- With Skill 的那次失败也只剩 `storage` / `redis` 两个 summary 主测未过，说明 skill 已经显著提高了覆盖率，但不是绝对保底。

## 📁 标准目录结构说明

```text
.
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── control-plane/
│   ├── mirror-service/
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
