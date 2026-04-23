# Real Estate Legal 模板任务说明

## 第一部分：任务设计参考

* **Skill 价值定位**：技能收益必须体现在降低真实房地产拍卖尽调的漏项率和收敛成本，例如公告变更识别、司法/非司法 sale status 判断、lien priority、surviving debt、occupancy risk、IRS/federal redemption、HOA split、估值折扣和 bid cap。严禁把 skill 设计成答案泄漏、固定字段模板、verifier 专用提示、或替代真实证据链的硬编码清单。

* **任务目标形态**：任务应要求 Agent 从多份真实风格资料中完成法律/商业判断，输出结构化尽调报告和可读 memo；应让无 skill solver 理论上可解，但需要自行建立拍卖法律审查路径。不应做成修复 app、单文件抽取、谜题、隐藏答案匹配、纯静态表格填空，或只靠泛泛法律 disclaimer 过关的任务。

* **验证设计重点**：Verifier 应关注行为结果和证据一致性，包括 sale status 是否合理、关键 claim 是否分类正确、风险是否被实质覆盖、估值公式是否可复算、memo 是否与 JSON 一致、防作弊是否能阻止改输入/伪造 source_id/引用测试。Verifier 不应绑定唯一措辞、唯一实现路径、某个脚本输出，或要求 instruction 未说明的隐式格式。

## 第二部分：示例任务

### 📌 任务元数据

- 任务名：`trustee-sale-diligence-report`
- 目录：`/home/lenovo/skill/Harbor/skill_moban/business/real-estate-legal/template_new`
- 类别：`real-estate-legal`
- 难度：`hard`
- 标签：`real-estate-legal`, `foreclosure`, `auction`, `title-review`, `lien-priority`, `legal-risk`, `valuation`, `document-analysis`
- 绑定 Skill：`leiloeiro-edital`, `leiloeiro-juridico`, `leiloeiro-avaliacao`

任务要求 solver 根据本地 trustee-sale 资料包，输出结构化 JSON 尽调报告和 Markdown 投资备忘录，判断 sale status、lien priority、surviving debt、legal/possession risk、估值和 `BID_WITH_CONDITIONS` 推荐。

### 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）

Verifier 策略：

- 主测：校验输出 schema、property/sale facts、claim priority/treatment、risk flags、valuation formula、recommendation logic、evidence grounding、memo/JSON 一致性。
- 防作弊：校验输入资料包 SHA256，拒绝篡改 `/root/input/auction_packet/`；拒绝伪造 source_id；拒绝输出引用 verifier/test/hidden answer；拒绝泛泛 disclaimer-only memo。

多模态：

- 不适用（纯文本、CSV、JSON、YAML 法律/房产资料包任务）。

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是提供拍卖公告审查、法律风险识别、占用/债务审查和估值安全边际的结构化框架；without-skill 理论上仍可解，但更容易漏掉 tenant possession、HOA split、IRS/federal redemption、dismissed bankruptcy 与 surviving-debt 口径。

基于最终冻结版本最近 `3` 次有效 task-level 对比实验（均为 `codex + gpt-5.4`，已排除此前 skill 临时改动与启动失败样本）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `66.7%` | 近 `3` 次有效对照里，Without Skill 不如 With Skill，原因是更容易漏掉 tenant/possession risk、recommendation 条件和 evidence grounding |
| Agent 执行耗时 | `273.0s` | `279.7s` | With Skill 的平均 Agent 耗时基本持平，未体现明显速度优势；本任务的收益主要来自尽调漏项率下降 |
| Input Tokens | `0.226M` | `0.280M` | With Skill 因加载原始 SkillsMP skill 上下文，平均 input tokens 约为 Without Skill 的 `1.24x`；本轮 token 未下降 |

### 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── readme.md
├── environment/
│   ├── Dockerfile
│   ├── input/
│   └── skills/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    └── solve.sh
```
