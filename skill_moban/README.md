# Harbor Skill Template Pipeline

本文档用于规划并执行 Harbor `skill_moban` 新模板任务的构建流程。目标是在指定大类/小类目录下，为 SkillsMP 对应分类中的热门 skill 设计可运行、可验证、可复现实验结果的模板任务，并产出可打包交付的最终文件。

---

# 第一轮提示词：先设计，不做实验

---

把下面提示词发给负责构建模板的 Codex：

（示例输入：）

```bash
TEMPLATE_PATH=/home/lenovo/skill/Harbor/skill_moban/business/ecommerce
SKILL_PATH=https://skillsmp.com/categories/ecommerce
```

约束：

- 模板任务必须新建在对应小类目录的 `template_new/` 下。
- skill 必须通过 `npx add` 方法安装到任务的 `environment/skills/` 下。
- 无论任何阶段，都不能修改既定 skill 本体。
- with_skill 与 without_skill 的唯一区别，只能来自 `environment/skills/` 及对应环境复制逻辑。
- 不能额外改题面、测试、数据、依赖或 skill 来制造实验差异。
- 每次 E2B 任务必须新建隔离环境；旧任务 runtime 和环境可以删除。
- E2B 运行环境与方法参考：
  - `/home/lenovo/skill/Harbor/skill_moban/.e2b_cloud_run.env`
  - `/home/lenovo/skill/Harbor/skill_moban/e2b_cloud_run.md`
- 主 agent 可以分配多个 Codex 子 agent 工作。
- 在未拿到最终 `README.md` 所需的全部实验结果前，不停止。
- Skill 选择规则：
  - 优先参考 `SKILL_PATH` 对应 SkillsMP 分类页面，再结合 skills.sh 补足候选。
  - 选择标准：
    - 优先选择 Stars 更高、安装量更高、质量更稳定的热门 skill。
    - 记录候选 skill 的 stars 数，最终 README 之外需要向用户说明至少参考了 10 条热门 skill 及 stars。
    - 不选择依赖外部私有账号、特殊权限状态、付费后台、个人隐私数据或高敏感安全操作的 skill。
    - 除非 skill 的 “when to use” 明确只提到或重点提到修复场景，否则不要设计修复类任务。
    - Skill 的 “when to use”、核心工作流、输入输出习惯必须和 instruction 的任务类型匹配。


```text
先不要做实验！

先完成以下设计并给我看：
1. 挑选你要绑定的热门 skill：
   - 使用 npx add 方法安装到 environment/skills/ 下。
   - 说明该 skill 的 stars 数。
   - 不要选择依赖外部私有账号、特殊权限状态，或伴随隐私/安全风险的高敏感度 skill。
2. 选定任务输入数据来源：
   - 说明输入数据文件。
   - 给出相应参考链接。
   - 数据可以来自网页抓取，但任务内数据必须保持确定性和可测性。
3. 设计完整 instruction.md：
   - 写入题面的 instruction.md 必须是英文。
   - 给我看的说明可以用中文输出。
   - 题面只保留症状、业务约束、交付合同和禁止事项。
   - 弱化或移走 skill 应该提供的诊断细节。

除非 skill 的 “when to use” 明确只提到或重点提到修复场景，否则不要设计修复类任务。

TEMPLATE_PATH=/home/lenovo/skill/Harbor/skill_moban/business/ecommerce
SKILL_PATH=https://skillsmp.com/categories/ecommerce

模板任务必须新建在 TEMPLATE_PATH/template_new/ 下。
无论发生什么，都不能修改既定 skill。

写 README 和 instruction 时，避免使用以下表达：
- “冻结”
- “真实”
- “不是...而是”

E2B 运行环境和方法参考：
- /home/lenovo/skill/Harbor/skill_moban/.e2b_cloud_run.env
- /home/lenovo/skill/Harbor/skill_moban/e2b_cloud_run.md

每次新起 E2B 任务时必须新建隔离环境，因为会有很多任务并行运行。旧任务 runtime 和环境可以删除。
无论何时 skill 都不能修改。

你的任务：
请为一个新的 TEMPLATE_PATH 模板任务设计完整方案。该模板用于模拟 SKILL_PATH 中热门 skills 的典型任务案例。任务目录风格对齐 Harbor skill_moban 模板，并满足：

1. 任务必须可验证、可运行，不能像 puzzle，也不能靠隐藏答案文件取巧。数据可以从网上爬取。
2. oracle 必须稳定通过全部测试，并在 E2B 云端通过。
3. 正式对照实验中，without_skill 不能完全通过，且失败必须偏行动或分析层面。格式问题可以适当放宽，除非 skill 明确要求格式。
4. 如果 without_skill 超时，也算不通过；timeout_sec 写入 task.toml。时间上限取 with_skill 做题时间 2 倍后向上靠近的 100 秒倍数，并与 600 秒取较大值。如果超时后 verifier 仍全通过，则算通过。
5. with_skill 和 without_skill 的唯一区别必须只来自 environment/skills/ 及对应环境复制逻辑，不能额外改题面、测试、数据、依赖或 skill。
6. verifier 每个测试点都要测试，不能测到一半中途退出。
7. task.toml 不要透露作者信息。

最终只能保留以下结构；若有额外文件，最终完成后清场：

模板任务：
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── ...
│   └── skills/
├── tests/
└── solution/

并生成相应 README.md。

instruction.md 写法要求

`instruction.md` 使用英文，简洁为主。

推荐结构：

```markdown
You ... 

Input data is located at ...
- ...: ...
- ...: ...

Your task:
1. ...
2. ...

Output:
...

Notes:
...
```

设计要点：

- 开头简短描述核心任务。
- 输入数据只写任务内路径和极简说明，不写外部链接。
- “Your task” 只写要做什么。
- “Output” 写清楚产物文件和必要格式要求。
- “Notes” 放业务约束、禁止事项和必要边界。
- 不在题面写 verifier、测试文件、测试策略或 skill 内部诊断步骤。
- 保留交付合同，减少对 skill 方法论的明示。

environment 设计要求

- 使用单容器实现。
- 可以从网上爬数据，但 README 中要写明参考来源；instruction 中不要写链接。
- 数据要具备业务结构复杂度，同时保持确定性和可测性。
- Dockerfile 中不要出现 `codex_home`、`CODEX_HOME`、`npm install codex` 等污染运行环境的语句。
- skill 应出现在 Codex 工作区，并通过环境复制逻辑参与 with_skill 实验。
- 不允许通过修改 Dockerfile、依赖、题面、数据或测试来制造 with_skill 和 without_skill 差异。

verifier 设计要求

Verifier 包含：

- 主测试：覆盖任务交付合同中的每个关键产物和业务约束。
- 防作弊测试：检查硬编码、偷看测试、绕过数据处理、伪造输出等行为。

要求：

- 每个测试点都必须运行，不能中途退出。
- 测试可以适当放宽格式细节，重点验证行动与分析质量。
- 不需要检查 skill hash。
- oracle 必须稳定 100% 通过。
- without_skill 至少保留一项 verifier 失败。

README.md 写法要求

文件名必须是 `README.md`。

README 应在模板任务设计完成、并综合 SkillsMP 对应分类热门 skills 和任务流程后撰写。内容要干净、简洁、突出核心重点。

推荐结构：

```markdown
# XXX Template

这是面向 XXX 类 skill 的模板。它综合参考 SkillsMP XXX 类热门 skill 的共性能力：....

## 第一部分：任务设计参考

* **Skill 价值定位**：...
* **Verifier 设计重点**：...

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：...
- 类别：XXX
- 绑定 Skill：...
- 输入数据参考来源：
  - `environment/data/...`：任务内...；设计形态参考...
    【...】链接

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| ... | ... | ... |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| ... | ... |

### ⚡ Skill 相关性评估

结论：强相关。...

基于最近 **n** 次有效对比实验（n >= 3，均跑到 task-level 且存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `...` | `...` | ... |
| Agent 执行耗时 | `...` | `...` | ... |
| Tokens | `...` | `...` | ... |

## 📁 标准目录结构说明
```

README 约束：

- “任务设计参考”部分不写具体参考的 10 条热门 skill 列表；该列表只在对话中回答用户。
- “输入数据参考来源”必须包含任务内数据路径和相应链接；没有明确链接的数据不要写入该部分。
- Skill 相关性评估之后不要继续扩展无关内容，但需要保留标准目录结构说明。
- 写作时自查，避免出现不希望使用的表达。
```
```

---

# 第二轮提示词：翻译与设计审查

---

第一轮 Codex 输出设计后，继续发送：

```text
把 skill 翻译给我看。

请自我审查并修改：
1. 用中文告诉我你的 instruction 是否做到：
   - 保留题面必须交代的交付合同；
   - 弱化或移走 skill 有关的任何细节。
2. 告诉我你的 Dockerfile 设计。
```

## 人工检查点：

- Skill 和 instruction 是否相关：
  - 重点看 skill 的 “when to use” 和题面是否匹配。
  - 例如 skill 明显用于新建 app，题面却要求修改现有 app，则需要重做。
- 题面质量：
  - 是否像业务任务。
  - 是否可运行、可验证。
  - 是否避免 puzzle 化。
- Dockerfile：
  - 不应出现 `codex_home`、`CODEX_HOME`。
  - 不应出现 `npm install codex`。
  - 不应把 skill 写死成不规范格式。

---

# 第三轮提示词：进入迭代实验

---

人工确认 skill、instruction 和 Dockerfile 初版后，发送：

```text
就按现在的 skill 和 instruction 作为初版进行迭代吧。

不达目的不准停。

with_skill 和 without_skill 的唯一区别，必须只来自 environment/skills/ 及对应环境复制逻辑，不能额外改题面、改测试、改数据、改依赖、改 skill。
不能改 skill 本体。

without_skill 的失败必须偏行动或分析层面。格式问题可以适当放宽，除非 skill 里特别有格式要求。

对比实验方法见：
/home/lenovo/skill/Harbor/skill_moban/e2b_cloud_run.md

对比实验时，skill 应出现在 Codex 的工作区，但 Dockerfile 里不得出现 codex_home 类语句。
```

## 人工检查点：

- oracle 在 E2B 云端稳定通过全部测试。
- with_skill 有有效成功轨迹。
- without_skill 有有效失败轨迹，且失败原因偏行动或分析层面。
- 至少完成 3 次有效对比实验。
- 记录通过率、Agent 执行耗时、Tokens。
- 排除启动失败类 trial 后再写 README 的 Skill 相关性评估。

# 最终复核清单

在提交最终模板前逐项检查：

- Dockerfile：
  - 无 `codex_home`、`CODEX_HOME`。
  - 无 `npm install codex`。
  - 环境干净，单容器可运行。
- Skill：
  - 来自 `npx add` 安装。
  - 格式正确。
  - 未修改 skill 本体。
  - 实验轨迹中能看到 skill 被触发或被使用。
- instruction：
  - 英文。
  - 任务质量足够高。
  - 只交代任务、数据、输出和业务约束。
  - 未泄漏测试策略或 skill 诊断步骤。
- verifier：
  - 主测试和防作弊测试均覆盖。
  - 每个测试点都会执行。
  - oracle 100% 通过。
  - without_skill 至少有一项失败。
- 对照实验：
  - with_skill 与 without_skill 的差异只来自 `environment/skills/` 及复制逻辑。
  - 至少 3 次有效 task-level 对比实验。
  - 有完整 agent 轨迹。
- README：
  - 包含任务设计参考、示例任务、验证与测试指标、Skill 相关性评估、标准目录结构说明。
  - Skill 相关性评估使用最终实验结果。
  - 不把轨迹链接写入 README。
- 清场：
  - 最终目录只保留要求文件。
  - 删除临时文件、草稿文件、缓存文件和多余实验产物。

## 最终目录结构

模板任务最终只保留：

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── ...
│   └── skills/
├── tests/
├── solution/
└── README.md
```

轨迹文件不要放入 README。按以下结构存放到：

```text
/home/lenovo/skill/Harbor/skill_moban/skill_VS_noskill_trace/
└── 大类/
    └── 小类/
        └── 轨迹对比文件/
```

不要移动或修改该目录下其他已有文件。

最终对话输出：

- 说明模板任务目录。
- 说明参考了哪些热门 skills，并标明 stars 数，至少 10 条。
- 给出一条 without_skill 失败轨迹链接。
- 给出一条 with_skill 成功轨迹链接。
- 简要说明 oracle、with_skill、without_skill 的最终实验结论。


