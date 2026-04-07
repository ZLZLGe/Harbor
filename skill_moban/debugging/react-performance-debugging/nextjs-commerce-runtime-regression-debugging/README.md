# debugging类模板任务

## 任务元数据
- 任务名称：`nextjs-commerce-runtime-regression-debugging`
- 类别：`debugging`
- 难度：`hard`
- 标签：`debugging`、`react`、`nextjs`、`browser-testing`、`hydration`、`cls`、`lazy-loading`、`interaction-latency`
- 描述：修复一个 Next.js 前端运行时回归任务，重点是冷启动不稳定、advanced 提前加载、重复交互退化。
- 提供的技能：
  - `browser-testing`：统一的浏览器复现与测量方法。
  - `measure.ts`：测页面加载和网络 waterfall。
  - `measure-review-entry.ts`：复现冷启动和错误 review entry。
  - `measure-interactions.ts`：检查重复交互后的退化。
  - `measure-cls.ts`：测页面视觉稳定性。

## 数据质量
- 结论：`通过`
- 数据不是手写 toy 数据。
- 当前快照一共 `10` 条书目。
- 数据都指向 `www.gutenberg.org`。
- 隐藏服务 [server.ts](./environment/api-simulator/src/server.ts) 直接返回这份数据，基线和 oracle 也都通过了真实数据断言。

## Oracle 结果
- 通过/失败状态：`通过`
- 奖励：`1.0`
- 通过的测试：`9 passed`
- 时间：`16.82s`
- 结果文件： [2026-04-07_oracle_verifier.txt](./validation/2026-04-07_oracle_verifier.txt)

## Verifier 设计与合理性
- 结论：`通过`
- 主测试 [test_performance.py](./tests/test_performance.py) 直接检查三件事：冷启动稳不稳、advanced 是不是晚加载、重复交互后会不会越来越慢。
- 防作弊测试 [test_guardrails.py](./tests/test_guardrails.py) 继续拦截改隐藏服务、绕开真实路径这类伪修复。
- 结果也能说明这个 verifier 有区分度：buggy 基线是 `3 failed, 6 passed`，oracle 是 `9 passed`。

## 多模态验证
- 结论：`当前任务不适用`
- [task.toml](./task.toml) 把任务标为 `debugging`，重点就是前端和浏览器运行时。
- 当前输入面是 `/app`、隐藏服务和浏览器，不是音频、PPTX、视频、PDF。

## skill 与任务强相关性
结论：`强相关`。没有 skills 时，模型虽然并非完全无法完成任务，但会明显更慢，也更依赖自己摸索检查路径；引入这组 browser-testing skills 后，模型能更早进入浏览器验证并直接围绕冷启动、advanced 延迟加载和重复交互退化展开排查。量化对照见 [2026-04-07_skill_evidence.md](./validation/2026-04-07_skill_evidence.md)：with-skills `563.1s`，without-skills `623.3s`，快 `60.2s`；原始轨迹见 [2026-04-07_redesign_with_trajectory.json](./validation/2026-04-07_redesign_with_trajectory.json) 和 [2026-04-07_redesign_without_trajectory.json](./validation/2026-04-07_redesign_without_trajectory.json)。

## 维护者建议
状态：`APPROVE`。该任务强依赖浏览器复现与运行时测量，Oracle 结果稳定通过且奖励为 `1.0`，同时 verifier 兼顾主症状和防作弊约束，符合基准测试里的 “Skill-dependent” 要求。

## 模板任务结构分类
- `instruction.md`
  任务说明。只放 solver 可见的症状、业务约束和禁止事项。
- `task.toml`
  任务元数据，包括标签、技能要求、运行入口等。
- `environment/`
  任务运行环境。
- `environment/website/`
  待修复的前端应用代码。
- `environment/api-simulator/`
  隐藏服务或模拟后端，用来提供真实下游数据和运行时依赖。
- `environment/skills/`
  任务绑定的 skill 定义和配套脚本。
- `tests/`
  verifier 与 guardrail 测试。
- `solution/`
  参考修复和 `solve.sh`。
- `validation/`
  维护侧验证材料、轨迹摘要和必须归档的证据文件。
- `PLAN.json`
  任务规划或构建过程中的结构化元信息。
