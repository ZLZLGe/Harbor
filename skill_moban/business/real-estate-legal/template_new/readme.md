# Real-Estate-Legal Template

这是面向 `real-estate-legal` 类 skill 的模板。它综合参考 SkillsMP real-estate-legal 类热门 skill 的共性能力：拍卖公告审查、产权和留置权分析、司法/非司法 sale status 判断、占用与赎回风险识别、房地产估值、安全边际和投标建议生成。

## 第一部分：任务设计参考

* **Skill 价值定位**：real-estate-legal 类 skill 的核心价值，是把分散的公告、产权、法院、债务、占用和估值资料组织成严谨的尽调路径。模板任务应让 skill 降低漏掉 senior/surviving debt、notice defect、tenant possession、IRS/federal redemption、HOA split 等关键风险的概率，而不是替 Agent 泄露最终结论。
* **Task目标形态**：任务应要求 Agent 从真实风格的房地产拍卖或法律资料包中，产出结构化尽调报告、证据索引和可读投资/法律 memo。目标形态适合设计成多源证据核对、claim priority 分类、sale status 判断、风险分级、估值折扣和 bid/no-bid 推荐，不适合做单文件摘录、泛泛 legal disclaimer 或不可验证的主观建议。
* **Verifier设计重点**：Verifier 应验证法律/商业判断是否与输入证据和本地规则一致，而不是绑定唯一措辞或实现路径。重点应覆盖输入不可变、source_id 真实性、sale status、claim priority/treatment、risk flags、surviving debt、valuation formula、recommendation logic、memo/JSON 一致性和反 verifier/hidden-answer 引用。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`trustee-sale-diligence-report`
- 类别：`real-estate-legal`
- 难度：`hard`
- 绑定 Skill：`leiloeiro-edital`、`leiloeiro-juridico`、`leiloeiro-avaliacao`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 使用同一份 trustee-sale 资料包，独立推导 property/sale facts、claim priority、surviving debt、material risks、valuation 和最终投标建议。它关注尽调结论是否被证据支撑且可复算，而不是实现方式或措辞是否一致。

- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 输出 JSON/Markdown schema、金额数值类型和 required sections | 法律尽调报告与 memo 结构化输出 |
| property facts、corrected parcel、trustee、auction date、opening bid、sale status | 拍卖公告审查与 sale status 判断 |
| foreclosing lien、tax、municipal assessment、HOA split、IRS、judgment、released mechanic lien、solar filing | 产权链、lien priority 和 surviving debt 分析 |
| dismissed bankruptcy、tenant possession、IRS redemption、notice correction、code/condition、solar payoff uncertainty | 法律、占用、赎回和运营风险识别 |
| recommended_max_bid 公式、surviving_debt_total、BID_WITH_CONDITIONS 条件 | 估值安全边际、投标上限和推荐逻辑 |
| evidence_index、source_id 白名单、memo/JSON 一致性 | 证据链、引用约束和可审计交付 |
| 输入 packet hash、禁止 verifier/test/hidden-answer 引用、拒绝泛泛 disclaimer-only memo | 防作弊 guardrail 与真实尽调行为 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是提供拍卖公告审查、法律风险识别、占用/债务审查和估值安全边际的结构化框架；without Skill 理论上仍可解，但更容易漏掉 tenant possession、HOA split、IRS/federal redemption、dismissed bankruptcy 与 surviving-debt 口径。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `66.7%` | 近 3 次有效对照里，without Skill 更容易漏掉 tenant/possession risk、recommendation 条件和 evidence grounding；with Skill 明显提高尽调完整性。 |
| Agent 执行耗时 | `273.0s` | `279.7s` | With Skill 的平均 Agent 耗时基本持平，本任务收益主要体现在漏项率下降。 |
| Tokens | `0.226M` | `0.280M` | With Skill 因加载原始 SkillsMP skill 上下文，平均 input tokens 约为 Without Skill 的 `1.24x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── input/
│   └── skills/
├── tests/
├── solution/
└── readme.md
```
