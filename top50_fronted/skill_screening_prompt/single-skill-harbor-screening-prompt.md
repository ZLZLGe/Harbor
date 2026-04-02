# Single Skill Harbor Screening Prompt

你现在要评审一个已经下载到本地的单个 skill 目录，判断它是否值得保留，作为后续 Harbor 造题和小类 seed 模板归纳的输入。

你的目标不是直接生成 Harbor 任务，而是先做严格筛选。

## Target

- target_skill_dir: `<TARGET_SKILL_DIR>`

如果你发现这个目录并不是一个单独 skill，而是混入了多个无边界的 skill 子目录，请基于当前目录的主 skill 主体做判断，并在 `uncertainties` 中明确写出这个问题。

## Mandatory Reading Order

在给出结论前，你必须按下面顺序完成阅读与判断：

1. 递归探索 `<TARGET_SKILL_DIR>`，优先阅读：
   - `SKILL.md`
   - `README*`
   - `references/`
   - `docs/`
   - `scripts/`
   - `src/`
   - `configs/`
   - `templates/`
   - `examples/`
   - `fixtures/`
   - `package.json`
   - `pyproject.toml`
   - `requirements.txt`
   - 任何测试、样例、schema、配置或数据说明文件
2. 阅读 Harbor 参考：
   - `/home/levi/.codex/skills/harbor/SKILL.md`
   - `/home/levi/.codex/skills/harbor/references/task-format.md`
3. 阅读 Harbor task builder 参考：
   - `/home/levi/Harbor/codex_task_builder_v3/src/prompts.ts`
4. 再输出最终 JSON

不要只看目录名、标题或几段摘要就下结论。

## Decision Goal

你要回答的是：

1. 这个 skill 是否适合被转化为可验证、可复现的 Harbor 任务
2. 在该任务里，agent 使用这个 skill 是否会明显优于不用 skill

最终只能输出：

- `keep`
- `drop`

不允许输出 `maybe`。

## Harbor Fit Standard

一个 skill 可以被 `keep`，当且仅当它满足下面的大方向：

### A. Harbor taskability

这个 skill 适合被转化为 Harbor task 包，至少能合理支撑下面这些任务部件：

- `instruction.md`
- `task.toml`
- `environment/Dockerfile`
- `solution/solve.sh`
- `tests/test.sh`
- `tests/test_outputs.py`

你要特别判断：

- 任务是否可以做到 self-contained
- verifier 是否可以程序化、稳定、无歧义
- 环境是否可以复现
- 任务是否能在 Harbor 的单容器、轻量环境里成立
- 是否能稳定满足 reward 与路径契约

### B. Skill benefit

即使一个任务理论上可以造出来，也只有当这个 skill 会明显帮助 agent 时才可以 `keep`。

“会明显帮助 agent”指的是这个 skill 提供了独特的方法、结构、规则、检查框架、分解方式、工作流模式或领域组织方式，使得：

- agent 更容易完成任务
- agent 更容易通过 verifier
- agent 的正确率、稳定性或效率会明显优于不用该 skill

仅仅“主题相关”不算明显帮助。

## Important Boundaries

下面这些情况不能直接作为 `drop` 理由：

- skill 没有现成完整输入资产
- skill 主要是参考资料、方法论或检查清单

只要这个 skill 提供了足够清晰的规则、方法、结构或流程，使 Codex 在后续造题时可以合理合成输入、题面与 verifier，它仍然可能 `keep`。

但如果需要“凭空乱编”任务输入，或者 skill 只能提供非常泛化的主题灵感，没有清晰的方法锚点，就应该 `drop`。

## Strong Drop Signals

下面这些情况通常应直接判为 `drop`：

- 主要是安装、发布、marketplace、session 管理、agent router、平台导航
- 严重依赖私有账号、实时外部状态、企业内系统、人工审批
- 正确性主要依赖主观评价或开放式研究，难以写稳定 verifier
- 没有清晰的核心能力边界，太宽泛，难以收敛成 Harbor 任务
- skill 对 agent 没有独特收益，只是主题相关
- 即使强行出题，也很难做到 self-contained、可复现、可验证

## Required Checks

你必须显式检查并体现在结论里：

1. 这个 skill 能否支撑 Harbor 任务化
2. 这个 skill 是否包含独特方法或结构，而不只是泛化描述
3. 使用这个 skill 是否会让 agent 明显更强
4. 即使没有现成输入资产，是否仍可合理合成输入
5. 主要阻断点是什么
6. 你实际读了哪些文件
7. 哪些地方你仍然不确定

## Output Contract

你必须返回严格 JSON，且满足：

- 输出只能是 JSON，不要附加解释文本
- 字段必须符合 `/home/levi/Harbor/top50_fronted/skill_screening_prompt/output-schema.json`
- `files_reviewed` 必须列出你实际查看过的关键文件路径
- 如果信息不足，必须在 `uncertainties` 中明确写出
- 不确定的事情不能假装确定

## Output Semantics

字段含义按下面理解：

- `summary`
  对结论的简洁概括
- `harbor_task_adaptation_summary`
  为什么它适合或不适合被改造成 Harbor 任务
- `skill_benefit_rationale`
  为什么使用 skill 的 agent 会比不用 skill 更好，或者为什么不会
- `positive_signals`
  支持 `keep` 的关键正向信号；如果是 `drop`，可以为空
- `blocking_issues`
  关键阻断点；如果是 `keep`，可以为空
- `input_synthesis_feasibility`
  判断后续是否可以基于该 skill 合理造输入，而不是机械依赖现成资产
- `uncertainties`
  你无法确认、但会影响判断质量的问题

## Default Bias

默认偏严格。

只有当你能清楚说明：

- Harbor 任务怎么成立
- skill 为什么真能帮助 agent

才输出 `keep`。

否则输出 `drop`，并把原因写清楚。
