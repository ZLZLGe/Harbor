Academic Template

这是面向 Academic 类 skill 的模板。它综合参考 SkillsMP Academic 类热门 skill 的共性能力：证据优先研究、论文检索与筛选、引用管理、事实核查、方法学评估、文献综述与学术写作。

## 第一部分：任务设计参考

* **Skill 价值定位**：Academic 类热门 skill 的共同价值不只是“写得像论文”，而是把资料检索、证据核验、来源筛选、引用规范和方法学判断组织成稳定流程。任务应让 skill 帮助 Agent 更快识别真实来源、伪造来源、重复来源、证据边界和研究局限。Skill 收益应体现在学术判断质量和收敛效率上，而不是依赖隐藏答案、固定措辞或单一实现路径。

* **Task 目标形态**：Academic 模板任务应模拟真实研究交付物，例如 evidence packet、literature review、paper review、citation audit、annotated bibliography 或 submission-readiness check。输入应包含真实风格的论文元数据、噪声引用、研究范围和待验证 claims，让 Agent 需要综合多个来源做判断。输出应是可审阅的结构化成果，而不是只填一个静态字段或做纯格式转换。

* **Verifier 设计重点**：Verifier 应验证 Agent 是否真正完成学术证据链：来源是否可验证、引用是否一致、claim 是否逐条覆盖、结论是否没有越过证据、out-of-scope 与 fake source 是否被排除。对于 Academic 类任务，测试应关注行为结果和学术质量约束，而不是绑定唯一措辞。还应加入防作弊检查，防止 Agent 伪造 citation、硬编码答案、跳过困难 claim 或用不相关文献凑数。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`academic-evidence-packet`
- 类别：Academic
- 难度：`hard`
- 绑定 Skill：`academic-researcher`

### 📊 验证与测试指标（Oracle & Verifier）

Oracle：官方解法通过本地 scholarly evidence gateway 读取固定论文快照，生成 claim-level evidence matrix、clean BibTeX、source assessments 和 literature note。E2B oracle 结果为 Reward `1.0`，`9/9` 测试通过。

Verifier 策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 检查所有 claims 的覆盖、decision、corrected claim 和 rationale 是否符合证据边界 | 事实核查、证据支持判断、过度外推识别 |
| 检查 clean bibliography、rejected sources、evidence keys 是否一致且排除 fake/duplicate/out-of-scope 来源 | 引用管理、来源可信度评估、去重与范围筛选 |
| 检查 source assessments 与 literature note 是否包含研究设计、方法局限、retrieval/generation/evaluation caveats 和 research gaps | 论文方法学分析、文献综述组织、学术写作 |

### ⚡ Skill 相关性评估

结论：相关。这个任务里，Skill 的核心价值是把论文分析框架、方法学局限、文献综述结构和引用审查流程显式化；新增的 `source_assessments` 与 caveat 分层要求能拦住只完成 claim 表层分类、但没有稳定方法学归纳的解法。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `1/3` | without Skill 主要失败在 source assessment 或 claim decision 的学术判断细节；with Skill 至少一次完整通过。 |
| Agent 执行耗时 | `198.9s` | `185.3s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `6.8%`。 |
| Tokens | `247.1k` | `223.0k` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.11x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── evidence_gateway.py
│   ├── evidence_snapshot.json
│   ├── research_packet/
│   └── skills/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    ├── solve.py
    └── solve.sh
```
