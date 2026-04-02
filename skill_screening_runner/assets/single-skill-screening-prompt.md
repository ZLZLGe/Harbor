# Single Skill Harbor Screening Prompt

你现在要评审一个已经下载到本地的单个 skill 目录，判断它是否值得保留，作为后续 Harbor 造题的候选输入。

## Hard Constraints

- 只做读文件和判断，不要修改任何本地文件。
- 不要执行任何删除操作，包括但不限于 `rm`、`rmdir`、`unlink`、`git clean`、`git reset --hard`、删除目录或删除文件。
- 最终只能输出严格 JSON，不要附加任何解释文字。
- JSON 必须满足 `{{OUTPUT_SCHEMA_PATH}}` 对应的结构要求。
- 不确定的事情不能假装确定，必须写进 `uncertainties`。
- 允许联网，但本地目录与本地参考必须是主依据，不要把结论主要建立在外部网页摘要上。

## Language Contract

- JSON 字段名必须保持 schema 中定义的英文 key，不要翻译字段名。
- 结构化枚举值必须保持 schema 规定的英文合法值，不要把这些值翻译成中文：
  - `decision`: `keep` / `drop`
  - `confidence`: `low` / `medium` / `high`
  - `input_synthesis_feasibility.judgment`: `feasible` / `risky` / `not_feasible`
  - `container_feasibility.judgment`: `feasible` / `risky` / `not_feasible`
  - `representativeness`: `low` / `medium` / `high`
  - `harbor_taskability`: `low` / `medium` / `high`
  - `drop_reason_category`: `not_applicable` / `not_verifiable` / `container_unfriendly` / `too_external` / `too_broad` / `no_skill_advantage` / `ops_only` / `insufficient_signal` / `unknown`
- `capability_archetype` 不是自然语言说明，必须保持稳定、简短、小写的英文 slug，例如 `api_design`、`backend_patterns`、`validation_guardrails`。
- 除结构化字段与路径、文件名、代码标识符、协议名、专有名词外，其余解释性文本必须使用简体中文。
- 必须使用简体中文的字段包括：
  - `summary`
  - `harbor_task_adaptation_summary`
  - `skill_benefit_rationale`
  - `positive_signals`
  - `blocking_issues`
  - `input_synthesis_feasibility.rationale`
  - `uncertainties`
  - `seed_reuse_signals`
- 不要中英混写句子；如果必须保留英文，请只保留必要的路径、文件名、命令、代码符号或协议名。

## Target

- category_slug: `{{CATEGORY_SLUG}}`
- subcategory_slug: `{{SUBCATEGORY_SLUG}}`
- skill_dir: `{{SKILL_DIR_NAME}}`
- skill_id: `{{SKILL_ID}}`
- target_skill_dir: `{{TARGET_SKILL_DIR}}`

## Mandatory References

在给出结论前，必须同时参考：

1. 目标 skill 目录：`{{TARGET_SKILL_DIR}}`
2. Harbor skill：`{{HARBOR_SKILL_PATH}}`
3. Harbor task format：`{{HARBOR_TASK_FORMAT_PATH}}`
4. Harbor task builder prompt 参考：`{{BUILDER_PROMPTS_PATH}}`

## Screening Goal

你要回答：

1. 这个 skill 是否适合被转化为可验证、可复现的 Harbor 任务
2. 在该任务里，agent 使用这个 skill 是否会明显优于不用 skill
3. 这个 skill 在当前小类里属于什么能力原型
4. 它是否适合作为后续小类级 seed / 模板归纳时的代表样本
5. 通过该 skill 造出的任务是否真的适合在 Harbor 容器环境里运行

## Mandatory Reading Order

1. 先递归探索目标目录，不要依赖程序预整理摘要。优先阅读：
   - `SKILL.md`
   - `skill.md`
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
   - 测试、schema、配置、样例、说明文件
2. 再阅读 Harbor 参考
3. 再阅读 builder prompt 参考
4. 最后输出 JSON

## Exploration Policy

- 以本地 skill 目录为主，自己递归查看关键文件，再下判断。
- 允许联网补充，但只在本地信息不足以确认关键事实时使用。
- 如果联网得到的信息会影响判断，请在 `uncertainties` 里说明依赖了哪些外部补充。

## Decision Standard

默认偏严格。

只有当你能明确说明：

- Harbor 任务如何 self-contained 地成立
- Harbor 任务如何在容器环境里稳定运行，而不依赖宿主机特权、桌面交互、企业内系统或不可控外部状态
- verifier 如何程序化、稳定、无歧义
- 这个 skill 提供了独特方法、结构、规则、工作流或检查框架
- 使用该 skill 的 agent 会明显更强

才输出 `keep`。否则输出 `drop`。

如果 `container_feasibility.judgment = not_feasible`，则不能输出 `keep`。

## Important Boundaries

下面这些情况本身不能直接导致 `drop`：

- 没有现成完整输入资产
- 主要是参考资料、方法论或检查清单

只要它仍然能支撑 Codex 合理构造输入、题面和 verifier，就仍可能 `keep`。

但前提仍然是：

- 任务能够在 Harbor 的容器环境里 self-contained 地运行
- verifier 能在容器内稳定执行

## Strong Drop Signals

下面这些情况通常应判为 `drop`：

- 主要是安装、发布、session 管理、marketplace、router、导航型 skill
- 必须依赖 GUI、桌面会话、浏览器人工交互或长期登录态
- 必须依赖宿主机特权、systemd、内核能力、Docker-in-Docker、物理硬件或特殊设备
- 严重依赖私有账号、实时外部状态、企业内系统、人工审批
- 正确性高度依赖主观判断，难以写稳定 verifier
- 主题相关但没有独特方法或结构
- 边界过宽，难以收敛成轻量 Harbor 任务

## Required Output Fields

你必须输出这些字段：

- `decision`
- `confidence`
- `summary`
- `harbor_task_adaptation_summary`
- `skill_benefit_rationale`
- `positive_signals`
- `blocking_issues`
- `input_synthesis_feasibility`
- `container_feasibility`
- `files_reviewed`
- `uncertainties`
- `capability_archetype`
- `representativeness`
- `harbor_taskability`
- `seed_reuse_signals`
- `drop_reason_category`

字段补充要求：

- `capability_archetype`
  - 用稳定、简短的小写标签总结主能力原型，例如 `api_design`、`backend_patterns`、`validation_guardrails`
- `representativeness`
  - 评估它是否适合作为当前小类的代表 skill
- `harbor_taskability`
  - 单独评估它落成 Harbor 任务的难度与稳定性
- `seed_reuse_signals`
  - 列出后续做模板归纳时可复用的结构线索，例如输入模式、输出模式、verifier pattern、skill benefit shape
- `container_feasibility`
  - 单独评估该 skill 生成的任务是否适合在 Harbor 的容器环境中运行
  - 必须明确考虑依赖、权限、服务形态、外部系统、交互方式是否容器友好
- `drop_reason_category`
  - 若 `decision=keep`，必须写 `not_applicable`
  - 若 `container_feasibility.judgment=not_feasible`，则必须写 `container_unfriendly`
  - 若 `decision=drop`，必须从以下类别中选一个最主要原因：
    - `not_verifiable`
    - `container_unfriendly`
    - `too_external`
    - `too_broad`
    - `no_skill_advantage`
    - `ops_only`
    - `insufficient_signal`
    - `unknown`

## Output Contract

- 只输出 JSON
- 不要输出 Markdown 代码块
- 不要输出额外说明
- `files_reviewed` 必须只列你实际查看过的关键文件路径
