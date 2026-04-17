# Academic 模板任务说明

本模板面向 `academic` 类任务，重点适配 SkillsMP 中高相关的 `systematic-literature-review`、`citation-management`、`research-ops`、`fact-checker` 一类能力。核心不是“生成一段像论文的话”，而是围绕真实学术证据链做筛选、核引、结论收敛，并用可运行、可复核的行为结果验收。

## 模板范式

1. 任务场景必须锚定真实工作流，为 Skill 创造必要性  
任务的设定必须落在真实的学术交付场景中，如文献筛选、引文修复、证据表对齐等，以赋予所提供 Skill 明确的业务价值。坚决杜绝依赖隐藏答案文件或强行设置障碍的“解谜（Puzzle）”类任务。任务的难度应自然促使 Solver 去调用对应的 Skill，而不是为了用 Skill 而造任务。

2. Skill 的设计应定位于“标准化诊断路径”，而非直接输出答案  
在设计附带 Skill 的任务时，Skill 的输入输出必须是诊断性或辅助性的，例如提供文献元数据比对能力、提供引用格式的 linting 工具。

底线要求：剥离该 Skill 时，任务在理论上依然可解，例如通过纯代码逻辑或文本推断，但定位错误和模型收敛的成本应显著升高。  
设计禁忌：Skill 绝不能退化为“直接替模型作答”或“直接返回最终 diff”的后门。

3. Verifier 仅验证交付物结果，严禁与特定 Skill 调用栈强绑定  
验证机制（Verifier）的设计必须与具体的修复路径解耦。Verifier 只应负责核验最终生成的学术材料，如 `summary.md`、`references.bib`，是否与设定的 protocol、证据链以及提交流程完全一致。只要结果符合标准，系统应包容 Solver 对 Skill 的不同调用组合或绕过 Skill 的其他合法自研实现，不设唯一解。

4. 环境基建必须还原真实的上下游链路与 Skill 依赖  
为承载 Agent Skills，评测环境必须具备真实的工程厚度。任务环境中应预置冻结的元数据快照、本地校验 API、投稿构建脚本（Build Scripts）或等价的真实链路。所提供的 Skill 必须作为环境中可被实际调用的接口、工具脚本或类库存在，绝不能降维成纯静态的文本上下文比对。

5. Guardrails 需精准拦截“绕过 Skill 限制”的学术伪修复  
安全护栏（Guardrails）的设计必须针对 Agent 在缺乏真实 Skill 能力时常见的“逃课”行为。任务必须前置拦截以下伪修复手段：为了规避校验报错而直接删除综述结论、为了逃避数据对齐而清空证据表格、暴力替换真实的校验链路、篡改隐藏服务节点、放宽本地构建逻辑，以及针对测试集的硬编码作弊。

## 示例任务

### 📌 任务元数据

- 任务名：`systematic-review-evidence-package-repair`
- 类别：`academic`
- 难度：`hard`
- 标签：`academic`, `systematic-review`, `citation-management`, `research-ops`, `evidence-synthesis`, `bibtex`
- 绑定 Skill：`systematic-literature-review`

任务要求：修复拟投稿的系统综述证据包。Solver 需以任务提供的候选文献、文献缓存和元数据为事实依据，严格遵循 protocol，原地修复以下三份待投稿材料：
included_studies.csv：精准筛入符合纳入标准的研究。
references.bib：修正并对齐相关的参考文献。
summary.md：根据最终纳入的研究，重写并确保综述结论的准确性。
最终目标：确保全套材料前后信息一致，顺利通过预投稿的自动校验。

### 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- 测试用例：`7/7` 通过

Verifier 策略：
- 主测试：主要测修复后的 included_studies.csv、references.bib、summary.md 是否内容正确、彼此一致，并且能通过真实提交链路 build_submission.py 的校验，成功生成合格的
submission_package.json。
- 防作弊测试：主要测 solver 是否绕过正常修复流程，例如修改 protocol、构建脚本或底层数据，删除正式交付物，或试图从隐藏校验服务中直接获取标准答案。


数据来源：
候选文献来自：
- Che et al. 2021: https://doi.org/10.1186/s12986-021-00613-9
- Pavlou et al. 2023: https://doi.org/10.1001/jamanetworkopen.2023.39337
- Parr et al. 2024: https://doi.org/10.1016/j.diabres.2024.111893
- Trico et al. 2024: https://doi.org/10.1007/s00125-023-06045-9

多模态：

- 不适用（纯文本与结构化学术证据修复任务）。

### ⚡ Skill 相关性评估

结论：强相关。

这个任务里，Skill 的核心价值是把修复流程固定下来：先筛对研究，再对准参考文献，最后核查综述结论是否与纳入研究一致。没有 skill 时，solver 仍然理论可解，但需要自己补全筛选逻辑、参考文献核验逻辑和摘要约束；有 skill 时，可直接调用审计脚本与修复脚本，把诊断和收敛成本显著压低。

基于最近 `3` 次有效对照实验，且均为当前 binary 隐藏服务版本、真正进入 task-level 的 trial：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `3/3` | 最新 3 组有效对照里，with_skill 稳定通过，without_skill 全部未通过 |
| Agent 执行耗时 | `执行超时` | `54.8s` | without_skill未在规定时间内完成任务，相比with_skill在技能的帮助下迅速通过 |
| Input Tokens | `N/A` | `116.7K` | without_skill未在规定时间内完成任务 |


### 📁 标准目录结构说明

```text
.
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── academic-api/
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
