# Documents Template Design Reference: Word Redline Finalization

## 第一部分：任务设计参考

本模板参考 `documents` 类热门 skill 的任务设计方式，重点围绕 `word-documents`、`tracked changes`、`document automation`、`office document internals` 这一簇能力构造。设计目标不是让 Agent 修应用、猜隐藏答案或做开放式写作，而是让它在真实文档链路中完成一个可验证、可复现、可运行的结构化交付。

* **Skill 价值定位**：技能收益必须体现在“诊断路径标准化”和“最后一公里结构收尾”上，例如如何从 `comments.xml`、`customXml`、脚注、settings 和关系文件中定位真实审阅状态，并把可见内容与包内元数据一起收敛；严禁把 skill 设计成答案泄露、固定输出文件、隐藏 oracle、verifier hack 提示或只有 skill 才能读取的私有答案通道。
* **任务目标形态**：任务应要求 Agent 处理真实风格的 Office 文档包，产出可打开、可复用、结构完整的最终文档，并保留理论可解性；不应把任务做成纯静态 toy sandbox、单点字符串替换、只看截图的主观审美题、依赖网络即时状态的不可复现题，或“删掉复杂结构也能过”的伪文档任务。
* **验证设计重点**：Verifier 应关注行为结果和真实交付质量，包括可见文本、表格、脚注、页眉页脚、OOXML 包部件、relationships、content types、review metadata 和防作弊 guardrails；不应绑定某个唯一实现，也不应只检查最终文本而忽略文档包结构，更不能依赖隐藏答案文件或允许修改输入、测试、依赖、skill 来通过。

## 第二部分：示例任务

本示例任务是一份真实风格的 Word 红线定稿交付：solver 需要根据审阅决定，把带评论、tracked changes、脚注红线和结构化 review manifest 的 `.docx` 处理成可直接发送签署的 clean final `.docx`。

## 📌 任务元数据

- 任务 ID：`documents__vendor-addendum-redline-finalization`
- 任务名称：`Template: Vendor Addendum Redline Finalization`
- 任务类别：`documents`
- 任务难度：`hard`
- 官方输出：
  - `/app/output/vendor_addendum_final.docx`
- 绑定 Skill：`word-redline-workflows`
- 对照口径：`with_skill` 与 `without_skill` 的唯一区别只来自 `environment/skills/` 及其对应 runtime 剥离逻辑；题面、数据、测试、依赖和 verifier 完全一致。

这个任务模拟的是一条更贴近真实法务运营的 Word 定稿链路，而不是“替换几个占位符”。输入包同时包含：

- `word/document.xml` 中的正文与表格红线
- `word/footnotes.xml` 中的脚注红线
- `word/comments.xml` 中的 review refs
- `customXml/item1.xml` 中的结构化 review manifest
- `word/settings.xml` 中的 `trackRevisions`

solver 必须把这些层一起收尾，才能交付真实可签署的 final DOCX。

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- Job：`documents-redline-v2-oracle-e2b-20260422a`
- Trial：`task_with_skills_e2b__WQpffnb`
- Task checksum：`6c00e0f414112e3a69a29a738e971e6e4b33fa3eb581a1a00b2705f19894349b`
- 测试用例：`10/10` 通过

Verifier 策略：

- 主测：验证正式输出文件存在、是有效 DOCX、并且可被正常解析。
- 主测：验证最终正文、表格、页眉页脚和脚注都正确体现 `accept / reject` 决策。
- 主测：验证 `w:ins`、`w:del`、comment markers、`word/comments.xml`、comments relationship、comments content type 和 `w:trackRevisions` 都已清理。
- 主测：验证 `customXml/item1.xml` 中的 review manifest 仍存在，并且每条 item 都从 `pending` 变成与决策一致的 `resolved + resolution=...`。
- 防作弊：禁止修改输入红线 DOCX、输入 JSON 或 shipped skill 文件。
- 防作弊：禁止通过删除脚注、删除结构化 review 部件、重建极简新文档、或输出 stub 文件来规避真实红线处理。

数据来源：

- 数据是仓内冻结的采购法务增补协议红线样例，内容风格参考真实 Word 审阅工作流，但评测时不依赖外网抓取。
- 真实性来自真实 OOXML 包结构与多部件收尾链路，而不是依赖隐藏答案文件。

多模态：

- 不适用（纯文档自动化任务）。

## ⚡ Skill 相关性评估

结论：强相关，而且最终 hardening 版已经稳定满足我们想要的 task contrast：同一版最终模板下，`oracle=1.0`、`with_skill=3/3`、`without_skill=0/3`。

这个任务里，Skill 的核心价值不是泄露最终答案，而是把最容易漏掉的 Word 收尾链路标准化：

- 先用 `inventory_word_redline.py` 把 `comments.xml` 里的 `Review Ref`、`customXml/item1.xml` 里的 `decisionKey`，以及 `word/document.xml` / `word/footnotes.xml` 里的实际红线对应起来。
- 再用 `apply_redline_decisions.py` 同时处理正文、表格和脚注中的 `w:ins` / `w:del`。
- 最后补做 package cleanup：清理 `comments.xml`、comments rel、comments content type、`trackRevisions`，并把 review manifest 从 `pending` 收敛到 `resolved`。

从有效 `with_skill` 轨迹可以直接看到 agent 会主动读取：

- `/app/.codex/skills/word-redline-workflows/SKILL.md`
- `/app/.codex/skills/word-redline-workflows/scripts/inventory_word_redline.py`
- `/app/.codex/skills/word-redline-workflows/scripts/apply_redline_decisions.py`

随后再回到任务目录执行正式收敛，说明 skill 诊断脚本确实进入了 agent 工作流。

基于最近 `3` 次有效 `with_skill` trial 与最近 `3` 次有效 `without_skill` trial（均为真实 task-level 运行，存在完整 agent 轨迹；已排除中途中断样本）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 = 0%` | `3/3 = 100%` | With Skill 已稳定通过；Without Skill 最近 3 次有效样本均未通过 |
| 平均总耗时 | `344.8s` | `199.3s` | With Skill 更快，平均总耗时降低约 `42.2%` |
| 平均 Agent 执行耗时 | `250.1s` | `98.6s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `60.6%` |
| 平均 Input Tokens | `385,736` | `185,056` | Without Skill 的上下文与试错开销约为 With Skill 的 `2.08x` |

最近有效样本：

- With Skill：
  - `documents-redline-v2-with-skills-e2b-20260422a / task_with_skills_e2b__MF4HGVJ -> 1.0`
  - `documents-redline-v2-with-skills-e2b-20260422b / task_with_skills_e2b__GZWRgbG -> 1.0`
  - `documents-redline-v2-with-skills-e2b-20260422c / task_with_skills_e2b__MAKrD55 -> 1.0`
- Without Skill：
  - `documents-redline-v2-without-skills-e2b-20260422a / task_without_skills_e2b__xqHbYX4 -> 0.0`
  - `documents-redline-v2-without-skills-e2b-20260422b / task_without_skills_e2b__cR2tp9r -> 0.0`
  - `documents-redline-v2-without-skills-e2b-20260422c / task_without_skills_e2b__PVCmYw4 -> 0.0`

稳定性补充：

- 三个 `with_skill` 样本共享最终版 checksum `6c00e0f414112e3a69a29a738e971e6e4b33fa3eb581a1a00b2705f19894349b`
- 三个 `without_skill` 样本共享最终版 checksum `c70a569060145f94e23b39a457fb261e1382e8f67f74fc7f733ac107b7085442`

失败模式归纳：

- 三次 `without_skill` 都不是启动失败，也不是完全做不出文档，而是收敛到“表面可读但结构化定稿不完整”的解。
- 三次 `without_skill` 都稳定遗漏 `customXml/item1.xml`，因此无法通过 review manifest 相关主测与 guardrail。
- 三次 `without_skill` 的页眉都回退成了 `Vendor Services Addendum`，没有保住输入文档里的 `Vendor Services Addendum - Legal Redline`，说明它选择了“重建可见文档”而不是“在原 DOCX 包内完成真实定稿”。
- 这正是任务要考的 skill 差异：没有 skill 时，solver 仍能大致看懂红线逻辑，但更容易在脚注、manifest、settings 和 package cleanup 的最后一公里漏项。

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── readme.md
├── environment/
│   ├── Dockerfile
│   ├── build-scripts/
│   ├── data/
│   └── skills/
│       └── word-redline-workflows/
├── tests/
│   ├── test_outputs.py
│   ├── test_guardrails.py
│   └── test.sh
└── solution/
    ├── solve.py
    └── solve.sh
```

说明：

- `environment/` 采用单容器实现，容器内同时承载冻结红线文档、结构化 review manifest、脚注链路和 task-bound skill。
- `tests/` 同时包含主测试与 guardrails，验证真实 DOCX 行为结果，而不是某个唯一实现。
- `solution/` 提供官方参考求解；当前最终版已在 e2b oracle 与 3 组有效对照中完成验证。
