# Debugging Template

这是面向 `debugging` 类 skill 的模板。它综合参考 SkillsMP debugging / troubleshooting 类热门 skill 的共性能力：症状复现、浏览器探针、日志与网络追踪、性能量测、假设验证、根因定位、回归测试和防作弊 guardrails。

## 第一部分：任务设计参考

* **Skill 价值定位**：debugging 类 skill 的核心价值，是把“猜测式修复”变成可复现、可量测、可验证的排障闭环。模板任务应让 skill 标准化症状复现、trace / console / network evidence、性能基线、根因假设和修复后回归验证，而不是直接泄露补丁或把任务退化为静态代码修改。
* **Task目标形态**：任务应从真实线上症状出发，只提供表现层问题、业务约束和禁止事项，让 Agent 在高仿真运行环境中定位根因并修复。目标形态适合设计成浏览器运行时回归、长会话性能退化、异步状态漂移、资源加载异常、下游依赖不稳定或 CI / workflow 故障排查，不适合做已知根因的简单替换题。
* **Verifier设计重点**：Verifier 应验证修复是否经过真实运行链路、是否解决原始症状、是否保持业务数据与关键测试钩子不变。重点应覆盖复现路径、量化阈值、跨设备 / profile 稳定性、真实下游调用、长时序 soak、资源按需加载、回归防护，以及防止删除组件、篡改隐藏服务、伪造数据或硬编码通过。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`nextjs-analytics-dashboard-runtime-regression-debugging`
- 类别：`debugging`
- 难度：`hard`
- 绑定 Skill：`browser-testing`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 在真实 Next.js dashboard、隐藏 API simulator 和 Playwright 浏览器环境中复现三类线上回归：deeplink 冷启动不稳定、Advanced Insights 提前加载、长会话交互退化。它通过 DOM、CLS、网络请求、运行时 handler 数量和刷新耗时共同判断修复是否真正落到运行时行为上。
- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 校验 `/api/dashboard` 必须经过真实 simulator，响应耗时和 payload 符合冻结快照 | 真实下游链路验证、禁止伪造数据源 |
| 检查 homepage、告警 drawer 和真实告警内容可渲染 | 浏览器复现、DOM 定位、业务关键路径确认 |
| 在桌面与移动 profile 下验证 alert deeplink 稳定，过滤器不漂移，CLS `< 0.05` | deeplink 调试、视觉稳定性、跨 viewport 复现 |
| 要求 linked alert context 只出现在 drawer scope 内且不产生明显位移 | 状态归属、布局量测、局部上下文修复 |
| 验证 Advanced Insights 打开前不额外请求非关键 JS，点击后才加载 | network waterfall、lazy loading、资源回归分析 |
| 重复过滤、sidebar 切换和 timeline refresh 后限制 handler 泄漏、pulse fan-out 和 refresh latency | soak testing、内存 /事件泄漏定位、交互性能量测 |
| 校验隐藏 simulator、incident artifacts、`data-testid` 和目录结构未被篡改 | 防作弊 guardrails、真实故障现场保护 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把浏览器探针、deeplink 量测、network waterfall 和 soak 复现路径标准化，从而迫使 Agent 处理真实运行时回归；without Skill 更容易停在表面 UI 正常但 task-level 仍失败的解法。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 均未能同时修复 deeplink、按需加载和 soak 回归；With Skill 连续 task-level 全通过 |
| Agent 执行耗时 | `1332.2s` | `1682.7s` | With Skill 耗时更高，但换来完整探针复现与稳定收敛；without Skill 更快结束却稳定停在错误解 |
| Tokens | `0.69M` | `1.91M` | With Skill token 约为 without Skill 的 `2.78x`，主要用于浏览器探针、量测结果和回归验证上下文 |

## 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── website/
│   ├── api-simulator/
│   └── skills/
│       └── browser-testing/
├── tests/
│   ├── test.sh
│   ├── test_guardrails.py
│   ├── test_performance.py
│   ├── verify_dashboard.py
│   └── vendor/
└── solution/
    ├── fixed/
    └── solve.sh
```
