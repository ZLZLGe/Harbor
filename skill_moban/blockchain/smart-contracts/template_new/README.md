# Smart-Contracts Template

这是面向 `smart-contracts` 类 skill 的模板。它综合参考 SkillsMP `smart-contracts` 类热门 skill 的共性能力：合约组件搭建、状态更新约束、链上参数执行、常见协议骨架复用，以及把链上动作整理成可核对的本地交付物。

## 第一部分：任务设计参考

* **Skill 价值定位**：`smart-contracts` 类热门 skill 的共同价值，在于把协议组件拆成清晰的合约边界、状态更新规则和操作顺序。对于 `defi-protocol-templates` 这类 skill，重点是帮助 Agent 快速落下 staking、AMM、governance 这几类常见合约骨架，并把关键动作串成一条可复跑的工作流。
* **Task 目标形态**：这类任务适合设计成本地协议交付题，要求 Agent 依据公开来源整理出的输入包，在单容器内完成合约实现、脚本回放和报告输出。题面应明确输入、入口、输出合同和不可改范围，把更细的实现路线留给 solver 自主判断。
* **Verifier 设计重点**：Verifier 应优先检查链上动作是否齐全、合约状态演化是否一致、奖励与治理逻辑是否满足约束，以及报告是否和当前回放结果对齐。对这类任务，动作级行为校验、输入不可改、回放重跑一致性，通常比格式细节更重要。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`smart_contracts__governance_liquidity_launch`
- 类别：`smart-contracts`
- 难度：`hard`
- 绑定 Skill：`defi-protocol-templates`
- 输入数据参考来源：
  - `environment/data/spec/token_catalog.json`：任务内资产元数据；设计形态参考 Uniswap token metadata  
    <https://github.com/Uniswap/default-token-list/blob/main/src/tokens/mainnet.json>
  - `environment/data/spec/launch_plan.yaml`：任务内协议参数包；参数口径参考 Uniswap V2 pool mechanics  
    <https://docs.uniswap.org/contracts/v2/concepts/protocol-overview/how-uniswap-works>
  - `environment/data/spec/reward_program.csv`：任务内激励排期；设计口径参考 Uniswap liquidity mining program  
    <https://blog.uniswap.org/introducing-uni>
  - `environment/data/spec/reference/staking_rewards_notes.md`：任务内奖励累计说明；设计口径参考 Synthetix StakingRewards  
    <https://github.com/Synthetixio/synthetix/blob/develop/contracts/StakingRewards.sol>
  - `environment/data/spec/reference/erc20votes_notes.md`：任务内投票权 checkpoint 说明；直接来源于  
    <https://docs.openzeppelin.com/contracts/5.x/api/token/erc20#ERC20Votes>
  - `environment/data/spec/scenario_replay.json`：任务内回放序列；由模板根据上述公开材料整理生成，无单独公开下载链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 会完成本地协议实现、跑通 `run_launch.sh`、重放整条场景链路，并输出与当前部署结果一致的 `launch_report.json`。它依赖题内输入文件、当前合约实现和本地链上执行结果，不依赖隐藏答案文件。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出合同 | 检查 `launch_report.json` 是否存在、可解析，且包含要求的顶层字段和基础结构 | 先理解正式交付合同 |
| 协议行为重放 | 独立部署当前合约并重放同一场景，核对 LP、奖励、投票与治理动作结果 | 协议组件实现与动作编排 |
| AMM 与奖励约束 | 检查流动性份额、兑换结果、奖励累计、资金边界和退出路径 | 常见 DeFi 状态更新规则 |
| 治理执行链路 | 检查 delegation、proposal、vote、queue、execute 与参数更新结果 | 投票权与治理流程 |
| 报告一致性 | 校验报告中的稳定字段、步骤顺序和 actor 覆盖范围是否与 fresh replay 对齐 | 回放结果整理与可核对报告 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可改 | `spec/` 下输入文件哈希不得变化 |
| 静态报告防护 | 清空或污染旧报告后重跑入口，确认输出会按当前执行结果重写 |
| 动态 actor 扩展 | 在不改公开入口和动作族的前提下加入额外 actor，检查回放与汇总是否仍由输入驱动 |
| 权限与拒绝路径 | 检查未授权参数更新、低票权提案、过早执行等动作会被拦下 |
| 奖励边界 | 检查 claim 总量不会超过已注入奖励 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 staking、AMM、governance 三类常见合约模板压缩成一套可直接落地的本地实现路线；without Skill 更容易在 LP 份额、reward rollover、vote checkpoint、queue/execute 这些动作层细节上掉分。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 最近 3 次有效对照里，without Skill 都保留了 verifier 失败项；with Skill 3 次均完成全部 13 个测试点 |
| Agent 执行耗时 | `328.0s` | `315.6s` | With Skill 的协议拼装和回放收敛更快，平均 Agent 耗时降低约 `3.8%` |
| Tokens | `763,144` | `746,554` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.02x`，且失败集中在协议行为探针与状态约束上 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   │   └── spec/
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
