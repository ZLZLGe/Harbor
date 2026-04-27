# Education Learning Capture Template

这是面向 Education 类 skill 的模板。它综合参考 SkillsMP Education 类热门 skill 的共性能力：把课程生产、知识沉淀、评估验证、教程/文档流程转化为可复用的 agent 工作流，并用稳定证据和结构化输出约束质量。

## 第一部分：任务设计参考

* **Skill 价值定位**：Education 类热门 skill 的共同价值不是替 agent 记答案，而是把教学、文档、评估和知识复用流程标准化。高质量 skill 应帮助 agent 判断何时创建/更新 skill、instruction 或学习条目，并把一次课程事故沉淀为未来可调用的流程。
* **Task目标形态**：任务应模拟真实教育内容生产链路，例如课程发布、LMS 元数据、字幕/转写、rubric、review notes 和 CI 日志之间的交叉校验。输出应是可复用的学习捕获产物，而不是一次性修补、普通总结或隐藏答案。
* **Verifier设计重点**：Verifier 应检查结构、证据真实性、skill-vs-instruction 决策、现有知识去重、通用性和防规避。通用性用可脚本化代理指标验证，例如一次性 ID 不能污染通用流程、必须覆盖未来课程场景、必须引用真实文件/API/绑定 skill 证据。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：education__course-incident-learning-capture
- 类别：Education
- 难度：`hard`
- 绑定 Skill：update-skills

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解法读取课程事故 bundle、repository inventory、本地知识服务和绑定的 `update-skills` process skill，输出一个可复用的课程发布契约复盘 skill 以及结构化 capture report。
- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 校验 `SKILL.md` frontmatter、必需章节和 `capture_report.json` schema | 创建/更新 skill 的基本结构约定 |
| 校验 evidence source 可解析到真实 bundle 文件、本地 API 和绑定 process skill | 用真实证据捕获 durable learning，而不是编造总结 |
| 校验 rejected alternatives 覆盖 existing instruction、existing skill、新 instruction 等归属判断 | update-skills 的 skill vs instruction vs learning 决策 |
| 校验通用性分数、future scenario 覆盖和一次性 ID 反过拟合 | 判断学习是否足够通用且足够具体 |
| 校验输入 bundle 与绑定 skill 未被修改 | 防止替换真实链路、删功能或改 skill 规避问题 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把一次课程事故转化为“检查现有知识位置 -> 判断 skill/instruction/learning 归属 -> 写证据化可复用 skill -> 做质量检查”的标准流程；without Skill 即使能写出普通 skill，也会因为缺少绑定 process skill 证据和 update-skills 归属判断而失败。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 均缺少 `/workspace/environment/skills/update-skills/SKILL.md` 过程证据，无法通过 verifier；with Skill 均通过。 |
| Agent 执行耗时 | `160.8s` | `147.2s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `8.5%`。 |
| Tokens | `253,983` | `212,331` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.20x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── knowledge_service.py
│   ├── session_bundle/
│   └── skills/
│       └── update-skills/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    └── solve.sh
```
