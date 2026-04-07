# 基准报告


## 数据质量
- 结论：`成立`
- 证据：
  - 真实数据审计见 [2026-04-07_dataset_audit.json](./2026-04-07_dataset_audit.json)。当前快照共 `10` 条记录，样本标题包括 `Frankenstein; or, the modern prometheus`、`Moby Dick; Or, The Whale`、`Pride and Prejudice`、`Wuthering Heights`、`Alice's Adventures in Wonderland`。
  - 同一审计文件显示，全部 `htmlUrl` 域名都是 `www.gutenberg.org`，`downloadCount` 范围是 `52,794` 到 `178,271`。这支持“真实公开目录快照，不是 toy 数据”。
  - 隐藏服务 [server.ts](../environment/api-simulator/src/server.ts) 直接返回这份快照，并保留 `220ms` 延迟和 `x-catalog-snapshot = gutendex-fiction-en-2026-04-06`。
  - 当前 buggy 基线和 oracle 都通过了真实数据断言 `test_books_api_uses_real_snapshot`，见 [2026-04-07_baseline_verifier.txt](./2026-04-07_baseline_verifier.txt) 与 [2026-04-07_oracle_verifier.txt](./2026-04-07_oracle_verifier.txt)。

## 任务有效性
- 结论：`成立`
- 证据：
  - [instruction.md](../instruction.md) 只给用户可见症状、业务约束和禁止事项，没有直接给根因。
  - 当前 buggy 基线 [2026-04-07_baseline_verifier.txt](./2026-04-07_baseline_verifier.txt) 稳定失败 `3` 项，且失败点正好对应三类目标症状：
    - linked review 冷启动稳定性失败，实际漂移到 `Gothic Fiction`
    - advanced 打开后没有新增 JS 请求
    - 重复交互后的 runtime handler 泄漏，`delta=36`
  - 无提示成功样本仍然是直接做浏览器复现与修复，而不是提交额外材料，见 [2026-04-07_skill_evidence.md](./2026-04-07_skill_evidence.md)。这说明任务主体仍然是“真实运行时调试”，不是谜题式任务。

## Oracle 质量
- 结论：`成立`
- 证据：
  - 参考解入口 [solve.sh](../solution/solve.sh) 只替换 `5` 个目标文件：
    - [BookCatalog.tsx](../solution/fixed/src/components/BookCatalog.tsx)
    - [CompareWorkspace.tsx](../solution/fixed/src/components/CompareWorkspace.tsx)
    - [CompareAdvancedPanel.tsx](../solution/fixed/src/components/CompareAdvancedPanel.tsx)
    - [useShelfProbe.ts](../solution/fixed/src/hooks/useShelfProbe.ts)
    - [useReviewShelfState.ts](../solution/fixed/src/hooks/useReviewShelfState.ts)
  - 当前 oracle 验证见 [2026-04-07_oracle_verifier.txt](./2026-04-07_oracle_verifier.txt)，结果是 `9 passed in 16.82s`。
  - 这说明 Oracle 是直接修 runtime 故障并过 verifier 的短路径，不是靠额外编排或过度设计取巧。

## Verifier 设计与合理性
- 结论：`成立`
- 证据：
  - 主断言在 [test_performance.py](../tests/test_performance.py)，分别覆盖：
    - 冷启动与刷新后的 shelf 稳定性
    - advanced 点击前后的 JS 请求边界
    - 重复交互后的 runtime handler 累积
    - advanced 面板仍可见
  - 防作弊断言在 [test_guardrails.py](../tests/test_guardrails.py)，继续拦截：
    - 隐藏 catalog simulator 不可改
    - solver 输入面不可暴露 incident artifacts
    - 不能回退到通用资产桶
  - 区分度由当前实验直接证明：
    - buggy 基线：`3 failed, 6 passed`，见 [2026-04-07_baseline_verifier.txt](./2026-04-07_baseline_verifier.txt)
    - oracle：`9 passed`，见 [2026-04-07_oracle_verifier.txt](./2026-04-07_oracle_verifier.txt)
  - 因为 solver 已看不到 `/root` 摘要提示，而 buggy 版本的真问题只会在浏览器运行时暴露，所以 verifier 采用 Playwright 收集 live runtime 事实，而不是检查静态补丁形状。这个设计理由由当前基线失败形态和 [2026-04-07_skill_evidence.md](./2026-04-07_skill_evidence.md) 中的无提示成功轨迹共同支撑。

## 多模态验证
- 结论：`当前任务不适用`
- 证据：
  - [task.toml](../task.toml) 将任务标为 `debugging`，标签集中在 `react`、`nextjs`、`browser-testing`、`lazy-loading`、`interaction-latency`。
  - 当前输入面来自 `/app`、隐藏服务和浏览器运行时，不是音频、PPTX、视频、PDF。
  - 因此，本报告只能据实写“不适用”，不能把“维护者已完成多模态人工复核”写成既成事实。

## skill 与任务强相关性
- 结论：`强相关`
- 证据：
  - 当前有完整 A/B 数据的 `Agent-模型组合` 有 `codex / gpt-5.4`。整理后的证据见 [2026-04-07_skill_evidence.md](./2026-04-07_skill_evidence.md)。
  - 任务和 skill 的能力面完全重合：
    - 任务说明 [instruction.md](../instruction.md) 明确要求 `Reproduce and measure the live browser behavior yourself`。
    - skill 文件 [SKILL.md](../environment/skills/browser-testing/SKILL.md) 直接覆盖 `cold-start review stability`、`network waterfalls`、`repeated interaction behavior`。
  - 对照结果是 `redesign_20260407`：with-skills `1/1` 通过，`563.1s`；without-skills `1/1` 通过，`623.3s`。with-skills 快 `60.2s`。
  - 原始轨迹已归档到 [2026-04-07_redesign_with_trajectory.json](./2026-04-07_redesign_with_trajectory.json) 和 [2026-04-07_redesign_without_trajectory.json](./2026-04-07_redesign_without_trajectory.json)。
  - with-skills 更快，不是因为少做事，而是更早走到对的验证路径。轨迹里它在 step `29` 就明确加载 `browser-testing` workflow，step `36` 开始把“真实服务 + 浏览器复测”作为收尾主线，step `51` 和 step `72` 直接核对移动端冷启动、advanced 延迟加载和重复交互后的 handler 稳定性。
  - without-skills 虽然也做出来了，但前半段要自己补这套方法。它到 step `31` 才把三类 runtime 检查整理成计划，step `49` 和 step `53` 还先花时间看 build artifact 和 manifest，再启动 built app 做 live sanity check。
  - 因此，这里的强相关是有轨迹支撑的：skill 提供的不是额外提示，而是这道题真正需要的浏览器复现与测量方法，所以能更早收敛到正确解题路径。


 
