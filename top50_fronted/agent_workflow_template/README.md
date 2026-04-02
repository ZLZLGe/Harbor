# Agent Workflow Template

这个目录提供一个面向 `llm-ai` 小类中 `agent-workflow` 型 skill 的任务模板：

- [agent-workflow-template.yaml](/home/lenovo/skill/Harbor/top50_fronted/agent_workflow_template/agent-workflow-template.yaml)

参考来源不是复刻某个现成任务内容，而是学习 `jpg-ocr-stat/image-ocr` 这类 `1 similar + 3 transfer` family 的组织方式，再把它抽象成更适合 agent workflow 类 skill 的模板。

## 怎么用

后续使用时，输入材料只需要两份：

1. 一个目标 skill
2. 这个模板 YAML

生成思路按下面顺序理解即可：

1. 先看 `scope`

确认当前使用的是 `llm-ai / agent_workflow` 这个能力原型模板。

2. 再看 `family_spec`

用它决定 4 个任务各自的职责：

- `similar`
  选目标 skill 最典型、最自然的 agent 工作流场景。
- `transfer1`
  换任务背景和输入材料类型，但保留同一能力链。
- `transfer2`
  换主输出形态，但保留同一能力链。
- `transfer3`
  换到审计、诊断、恢复或约束满足侧重点，但保留同一能力链。

3. 再看 `instruction_scaffold_zh`

用中文骨架去写每个任务的 `instruction.md`。  
重点不是复述 skill，而是把任务背景、输入资产、目标输出、规则和成功条件写清楚。

4. 再看 `task_package_contract`

用它把任务真正落成 Harbor task 包：

- `task.toml`
- `instruction.md`
- `environment/`
- `environment/skills/`
- `solution/`
- `tests/`

这里的作用是告诉生成器每一部分最少应该满足什么，不让任务只停留在 prompt 层。

5. 最后看 `io_contract`

用它选择输入资产和输出形态：

- 输入优先使用本地可复现材料
- 主输出从模板推荐模式里选
- 如需辅产物，只作为补充，不替代主输出

## 使用时的一个直观例子

如果某个 skill 的强项是“把一个目标拆成若干步骤，并结合上下文材料产出结构化交付物”，那么可以这样套这个模板：

- `similar`
  做一次最自然的目标分解与执行汇总
- `transfer1`
  把输入从单一 brief 换成多份日志、说明、记录
- `transfer2`
  把输出从 JSON 报告换成 Markdown 执行摘要或行动清单
- `transfer3`
  把重点改成审计、检查、恢复或约束核验

## 这个模板的核心原则

- 模板约束的是“agent workflow 能力链”，不是某个固定题材
- 任务最终必须能落成真正的 Harbor task 包
- 任务说明可以抽象，但输出必须可判定
- `similar` 要像这个 skill 的典型用法
- `transfer` 要保持能力一致，但任务表面形态必须真正拉开差异
