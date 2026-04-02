# Skill 筛选标准总结

本文总结 `skill_screening_runner` 当前使用的 skill 筛选标准，目标是回答一个核心问题：

- 这个 skill 是否值得保留，作为后续 Harbor 造题的候选输入

这里总结的是“筛选标准”，不是输出字段定义本身。字段细节仍以 [screening_result_fields_zh.md](/home/levi/Harbor/skill_screening_runner/docs/screening_result_fields_zh.md) 为准。

## 1. 筛选目标

一次标准筛选，需要同时判断四件事：

1. 这个 skill 是否适合被转成可验证、可复现的 Harbor 任务。
2. 在这个任务里，agent 使用该 skill 是否会明显优于不用 skill。
3. 这个 skill 在当前小类里属于什么能力原型。
4. 它是否适合作为后续小类级 seed / 模板归纳的代表样本。

换句话说，筛选不是只看“主题相关不相关”，而是看它能不能真正支撑后续 Harbor 造题和模板沉淀。

## 2. 保留标准

默认口径偏严格。

只有当一个 skill 同时满足下面这 6 个判断点，才应该判为 `keep`：

1. 能说明 Harbor 任务如何 self-contained 地成立。
   也就是后续造题时，题面、输入资产、代码仓库和目标输出能够在本地闭环完成，而不是强依赖外部账号、外部系统或人工配合。
   例子：一个讲 `pytest` 回归测试设计的 skill，如果可以直接基于题目里给出的 Python 项目、失败测试和修复目标完成整道题，这种就更接近 `keep`。

2. 能说明 Harbor 任务如何在容器环境里稳定运行。
   也就是 agent 的主要操作路径可以在 Harbor 容器里完成，依赖关系清晰，执行过程不需要宿主机特殊环境。
   例子：一个讲 `eslint` 规则修复流程的 skill，如果题目只需要在容器里安装 Node 依赖、修改前端代码并运行 `npm test` 或 `npm run lint`，这种通常满足这一点。

3. 能说明 verifier 如何程序化、稳定、无歧义。
   也就是最后验收最好能通过脚本、测试、静态检查或输出比对自动完成，而不是主要靠人工主观判断。
   例子：一个讲 Django 安全配置检查的 skill，如果题目可以通过测试脚本验证 `DEBUG=False`、安全头开启、配置项存在与否，那么 verifier 就比较稳定。

4. skill 本身提供了独特的方法、结构、规则、工作流或检查框架，而不是只有泛主题描述。
   也就是这个 skill 需要带来可执行的做事方式，而不只是说“要重视安全”“要写好测试”这种大而泛的提醒。
   例子：一个 code review skill 如果明确给出“先找输入边界，再查权限，再查错误处理，再查回归风险”的固定检查框架，就比只写“认真 review 代码”更值得保留。

5. 使用该 skill 的 agent 会明显更强，而不是只得到一些常识性提醒。
   也就是 skill 要能带来清晰的优势，让会用它的 agent 在完成任务时更快、更准或更稳定。
   例子：一个前端测试 skill 如果提供了“优先测试用户可见行为、避免绑定实现细节、按交互路径拆测试”的规则，那么会用该 skill 的 agent 往往比不会用的 agent 更容易写出稳定测试。

6. 通过该 skill 造出来的任务，整体上要适合放进 Harbor 容器环境里跑。
   这是现在额外加上的硬门槛。即使前面几条看起来都不错，只要最终任务明显离不开 GUI、宿主机特权、systemd、硬件设备或长期外部状态，也不应 `keep`。
   例子：一个讲桌面浏览器人工渗透流程的 skill，就算内容很专业，如果核心操作必须依赖图形界面、人工登录和宿主机网络环境，仍然应该判 `drop`。

一个更实用的理解方式是：

- 如果这个 skill 能稳定落成一道轻量、可复现、可验收的 Harbor 任务，而且该任务明显体现了 skill advantage，就偏向 `keep`。
- 如果只是“主题沾边”，但没有清晰的任务化路径、没有 verifier 抓手、没有明显的 skill 增益，就偏向 `drop`。

现在还要额外加上一条硬门槛：

- 如果通过该 skill 造出来的任务明显不适合放进 Harbor 容器环境里跑，就不应 `keep`。

## 3. 不能直接判掉的情况

下面这些情况本身不能直接导致 `drop`：

- 没有现成完整输入资产。
- 主要内容是参考资料、方法论、检查清单。
- 目录里只有少量文档，没有完整工程。

原因是当前筛选标准允许 Codex 在后续造题阶段合理构造输入、题面和 verifier。只要该 skill 仍然能支撑一个清晰、可验证的任务结构，就仍然可能 `keep`。

但这不等于可以忽略运行形态。如果它最终仍然离不开宿主机特权、GUI、硬件设备或不可控外部环境，依然应判 `drop`。

## 4. 强烈的丢弃信号

下面这些情况通常应判为 `drop`：

- 主要是安装、发布、session 管理、marketplace、router、导航型 skill。
- 明显依赖 GUI、桌面会话、浏览器人工交互或长期登录态。
- 明显依赖宿主机特权、systemd、内核能力、Docker-in-Docker、物理硬件或特殊设备。
- 严重依赖私有账号、实时外部状态、企业内系统、人工审批。
- 正确性高度依赖主观判断，难以设计稳定 verifier。
- 主题相关，但缺少独特方法、独特结构或独特工作流。
- 题目边界过宽，难以收敛成轻量 Harbor 任务。

这些信号背后的共同问题通常是三类：

- 任务无法 self-contained。
- 任务无法在 Harbor 容器环境里稳定运行。
- 验收无法程序化。
- skill advantage 不明显。

## 5. 评审时重点看什么

在实际筛选时，应该优先从以下角度判断：

- 任务化路径：
  - 能不能把它收敛成一类清晰的 Harbor 任务。
  - 输出物、修改点、验证方式是否具体。
- verifier 可行性：
  - 能不能写成程序化检查。
  - 是否容易出现“解释空间太大、没有唯一验收口径”的问题。
- 容器可行性：
  - 能不能放进 Harbor 容器里跑。
  - 是否依赖宿主机特权、桌面交互、systemd、特殊设备或不稳定外部状态。
  - verifier 是否也能在容器里稳定执行。
- skill 增益：
  - 这个 skill 是否给出明确规则、框架、反模式、清单、工作流。
  - 这些内容是否会让会用它的 agent 明显优于不会用它的 agent。
- 可归纳性：
  - 它是否代表当前小类的一类典型能力。
  - 后续能不能抽象成 seed/template。

## 6. 结构化判定字段该怎么理解

筛选结果里最关键的几个字段，其实对应的是几条不同的判断轴：

- `decision`
  - 最终结论：`keep` 或 `drop`。
- `confidence`
  - 对这个结论的把握程度，不等于 skill 质量本身。
- `representativeness`
  - 它是不是当前小类里的代表样本。
- `harbor_taskability`
  - 它落成 Harbor 任务的难度和稳定性。
- `container_feasibility`
  - 它生成的任务是否真的适合在 Harbor 容器环境中运行。
- `capability_archetype`
  - 它属于什么能力原型，方便后续归纳。
- `seed_reuse_signals`
  - 它身上有哪些结构可复用到模板沉淀。

这里要特别区分两件事：

- 一个 skill 可以 `keep`，但 `representativeness` 不一定高。
- 一个 skill 可以有明确能力价值，但 `harbor_taskability` 不一定高。

也就是说，“值得保留”不等于“最适合作为模板代表”，也不等于“最容易立刻落成 Harbor 任务”。

现在还要补上一层：

- 一个 skill 可以有明确能力价值，但如果 `container_feasibility = not_feasible`，仍然应被淘汰。

## 7. drop_reason_category 的使用口径

当 `decision=keep` 时：

- `drop_reason_category` 必须是 `not_applicable`

当 `decision=drop` 时，必须选择一个最主要原因：

- `not_verifiable`
  - 难以写稳定、程序化、无歧义的 verifier。
- `container_unfriendly`
  - 主要问题是任务本身不适合放进 Harbor 容器环境运行。
- `too_external`
  - 太依赖外部账号、外部服务、实时状态或企业内系统。
- `too_broad`
  - 边界过宽，难以收敛成轻量任务。
- `no_skill_advantage`
  - 主题相关，但 skill 不提供明显增益。
- `ops_only`
  - 更像运维、路由、导航、发布流程，而不是适合 Harbor 造题的 skill。
- `insufficient_signal`
  - 本地资产过于薄弱，无法支撑稳定判断。
- `unknown`
  - 无法更准确归类，但明确不应保留。

实践里最常见的几个 `drop` 主因通常是：

- `not_verifiable`
- `container_unfriendly`
- `too_external`
- `too_broad`
- `no_skill_advantage`

## 8. 推荐的实际判断顺序

为了减少误判，建议按这个顺序评审：

1. 先看这个 skill 能不能被任务化。
2. 再看它能不能在 Harbor 容器环境中稳定运行。
3. 再看 verifier 能不能稳定写出来。
4. 再看 skill 是否真的提供独特方法或结构。
5. 最后再判断它是不是小类代表样本，是否值得进入模板沉淀。

如果前 3 步站不住，通常就已经足够判 `drop`。

## 9. 一句总原则

可以把当前筛选标准压缩成一句话：

- 只有那些能够稳定转成自包含、可验证、能体现明显 skill advantage 的 skill，才应该保留。
- 现在还要求：这些任务必须适合在 Harbor 容器环境里运行。

如果只是“看起来相关”，但不能稳定造题、不能稳定验收、不能体现 skill 增益，就不应该进入后续 Harbor 流程。
