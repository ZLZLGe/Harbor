# Content-Creation Template

这是面向 `content-creation` 类 skill 的模板。它综合参考 SkillsMP content-creation 类热门 skill 的共性能力：品牌声音提取、长文写作、多渠道营销内容、商务邮件、内容发布流程、source-backed claim control 和反通用 AI 套话。

## 第一部分：任务设计参考

* **Skill 价值定位**：content-creation 类 skill 的核心价值，是把真实源材料转化为可复用的 voice profile 和跨渠道内容工作流。模板任务应让 skill 在 source evidence、brand voice consistency、claim boundary、channel adaptation 和 anti-cliche 上降低遗漏率，而不是只奖励“写得像营销文案”。
* **Task目标形态**：任务应要求 Agent 读取真实风格语料、campaign brief、claims、channel specs 和 glossary，先归纳品牌声音，再生成多渠道内容包和审计报告。目标形态适合设计成 source-derived voice profile、launch blog、LinkedIn、X thread、customer email、changelog 和 claim-safety audit，不适合做单篇作文、纯格式转换或不可验证的主观创意任务。
* **Verifier设计重点**：Verifier 应验证内容是否被真实 source_id 和 allowed claim_id 支撑，并检查跨渠道结构、长度、voice reuse、禁止短语、风险 claim 和审计记录。重点应覆盖输入不可变、本地 archive service 访问、source priority、excluded comparator sources、hard-ban taxonomy、claim coverage、channel constraints 和反 placeholder/verifier hack。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`content_creation__source_derived_brand_voice_pack`
- 类别：`content-creation`
- 难度：`hard`
- 绑定 Skill：`brand-voice`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 使用同一批冻结 source corpus、campaign brief、allowed claims、channel specs、glossary 和本地 archive service，独立验证 voice profile、content pack 与 audit report。它关注内容是否源于真实材料、引用是否可审计、claim 是否安全，而不是只看文案主观质量。

- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| `voice_profile.json`、`content_pack.json`、`audit_report.json` schema 和文件集合 | 结构化内容交付与审计输出 |
| source inventory、source priority、excluded comparator sources | 从真实材料归纳品牌声音，排除非 canonical 样本 |
| rhythm、claim style、evidence habits、lexicon、do/don't rules、hard bans | 可复用 voice profile 与反通用 AI 套话 |
| 各渠道 source anchors、allowed claim IDs、voice rules reuse | 多渠道内容改写和 claim grounding |
| channel length/format、X thread、email subject/preview、changelog note | 渠道适配与平台约束 |
| banned phrase、forbidden claim、unsupported number scan | claim safety、合规边界和内容质量 guardrail |
| archive service access log、输入/服务 hash、service health | 真实链路访问、防篡改和反静态捷径 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 source-first voice extraction、source priority、named hard-ban taxonomy、receipts over adjectives、claim boundaries 和 channel notes 标准化。最终 taxonomy 对照里 without Skill 三次有效实验全部失败，主要卡在 brand-voice hard-ban taxonomy、source-derived voice reuse 或 claim coverage；with Skill 保留通过样本。

基于最近 **3** 次有效对比实验（均真正跑到 task-level，已排除 E2B `ConnectError` 类启动失败 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33.3%` | 近 3 次有效对照里，without Skill 全部失败；with Skill 至少保留一个完整通过样本。 |
| Agent 执行耗时 | `376.4s` | `360.3s` | With Skill 平均 Agent 耗时降低约 `4.3%`。 |
| Tokens | `440,944` | `358,939` | Without Skill 的输入开销约为 With Skill 的 `1.23x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── hidden-service-src/
│   └── skills/
├── tests/
├── solution/
└── README.md
```
