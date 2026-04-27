# Documents Template

这是面向 `documents` 类 skill 的模板。它综合参考 SkillsMP documents 类热门 skill 的共性能力：Word/DOCX 读写、Office 文档自动化、tracked changes 处理、comments 清理、页眉页脚/脚注/表格保真、OOXML 包结构维护和最终可交付文件验证。

## 第一部分：任务设计参考

* **Skill 价值定位**：documents 类 skill 的核心价值，是把“看起来像文档”的输出提升为真实可打开、结构完整、可复用的 Office/PDF 交付物。模板任务应让 skill 在包结构诊断、跨部件遍历、格式保留、审阅痕迹清理和最终文件校验上降低漏项率，而不是泄露答案或只做表层文本替换。
* **Task目标形态**：任务应要求 Agent 处理真实风格的文档包，产出可被下游直接使用的 DOCX/PDF/Office 文件。目标形态适合设计成红线定稿、模板填充、合同/报告组装、批注处理、结构化元数据同步和格式保真交付，不适合做纯文本摘要、单点字符串替换、截图式交付或删除复杂结构也能过的伪文档任务。
* **Verifier设计重点**：Verifier 应检查真实文件行为和包内结构，而不只比较可见文本。重点应覆盖输出可解析、输入不可变、正文/表格/页眉页脚/脚注正确、tracked changes 和 comments 清理、relationships/content types/settings 收尾、customXml 元数据一致、结构未被扁平化以及防 stub/hidden-answer/verifier hack。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`documents__vendor-addendum-redline-finalization`
- 类别：`documents`
- 难度：`hard`
- 绑定 Skill：`word-redline-workflows`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 使用同一份带 tracked changes、comments、footnotes 和 `customXml` review manifest 的 Word 增补协议，按 `review_decisions.json` 独立生成 clean final DOCX。它关注最终文档是否真实可打开、结构完整、审阅链路已收尾，而不是实现脚本是否一致。

- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 输出 DOCX 存在、非空、可解包、可由 Word 解析 | 真实 Office 文件交付与基础有效性 |
| 正文、表格、页眉页脚和脚注按 accept/reject 决策收敛 | 跨部件 Word 红线处理和格式保留 |
| 清除 `w:ins`、`w:del`、comment markers、`comments.xml` | tracked changes 与 review comments 清理 |
| 清理 comments relationship、content type、`trackRevisions` | OOXML package cleanup 和 Word 设置收尾 |
| 保留并更新 `customXml/item1.xml` review manifest | 结构化审阅元数据同步 |
| 输入 DOCX、decision JSON、skill 文件 hash 不变 | 输入不可变与防篡改 guardrail |
| 表格、脚注、manifest 数量保留，输出大小合理 | 防止重建极简文档、删除复杂结构或 stub 输出 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值不是泄露最终答案，而是把最容易漏掉的 Word 收尾链路标准化：从 `comments.xml`、`customXml/item1.xml`、`document.xml` 和 `footnotes.xml` 建立审阅项映射，再同时处理可见红线和包级清理。without Skill 也能生成表面可读的 DOCX，但更容易漏掉 review manifest、脚注、settings 或 comments relationship 的最后一公里。

基于最近 **3** 次有效 with-skill trial 与最近 **3** 次有效 without-skill trial（均为真实 task-level 运行，存在完整 agent 轨迹；已排除中途中断样本）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | without Skill 三次均收敛到“表面可读但结构化定稿不完整”的解；with Skill 三次全通过。 |
| Agent 执行耗时 | `250.1s` | `98.6s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `60.6%`。 |
| Tokens | `385,736` | `185,056` | Without Skill 的上下文与试错开销约为 With Skill 的 `2.08x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── build-scripts/
│   ├── data/
│   └── skills/
├── tests/
├── solution/
└── README.md
```
