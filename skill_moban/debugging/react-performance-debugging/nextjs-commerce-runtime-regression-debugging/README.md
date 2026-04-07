# 模板任务

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

## 任务有效性
- 结论：`通过`
- [instruction.md](./instruction.md) 只写用户能看到的现象，没有直接告诉 solver 根因。
- buggy 基线稳定失败 `3` 项，正好对应三类目标问题：冷启动不稳、advanced 加载边界错误、重复交互退化。
- 成功样本的主要工作也是浏览器复现和 runtime 修复，不是靠额外材料过关。

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
- 结论：`强相关`
- 这道题本身就要求在浏览器里复现和测量问题，而 skill 覆盖的正是这几类浏览器检查。
- 量化对照见 [2026-04-07_skill_evidence.md](./validation/2026-04-07_skill_evidence.md)：with-skills `563.1s`，without-skills `623.3s`，with-skills 快 `60.2s`。
- 原始轨迹见 [2026-04-07_redesign_with_trajectory.json](./validation/2026-04-07_redesign_with_trajectory.json) 和 [2026-04-07_redesign_without_trajectory.json](./validation/2026-04-07_redesign_without_trajectory.json)。with-skills 更早进入浏览器验证，所以更快，也说明这个 skill 和任务是强相关的。

## 技能影响分析
- 没有 skills 时，模型不是完全做不出来，但会更慢，也更依赖自己摸索检查路径。
- 当前这组有效对照里，with-skills `563.1s`，without-skills `623.3s`，差了 `60.2s`。
- 原始轨迹显示，with-skills 更早进入浏览器验证；without-skills 先自己整理检查项，再回到 live runtime。
- 这说明 skill 的作用不是只补背景知识，而是把“该怎么查”直接变成可执行动作。

## 维护者建议
- 状态：`APPROVE`
- 理由：该任务强依赖浏览器复现与运行时测量，符合基准测试里的“Skill-dependent”要求。
- 理由：Oracle 结果稳定通过，奖励为 `1.0`，说明参考解可达且鲁棒。
- 理由：verifier 同时覆盖主症状和防作弊约束，不容易靠表面修补通过。
