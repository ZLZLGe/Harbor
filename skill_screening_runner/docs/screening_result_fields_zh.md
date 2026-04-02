# Skill 筛选结果字段说明

本文说明 `skill_screening_runner` 单个 skill 的标准结果字段，也就是输出目录下 `skills/*.json` 里的字段含义。

适用范围：

- `skills/<skill-dir>.json`
- `keep_index.json`
- `drop_index.json`

不完全适用范围：

- `logs/<skill-dir>.raw.txt`
- `retained_skills/<...>/`

原因是 `raw.txt` 保存的是模型原始输出；它可能没有完全满足 schema。真正会被后续流程消费和统计的是通过校验后的 `skills/*.json`。

`retained_skills/` 也不是这份文档的直接对象，因为它保存的是被判定为 `keep` 的原始 skill 目录副本，而不是标准化后的结构化 JSON。

## 先看一个重要区别

`skill_screening_runner` 的结果分两层：

1. 原始模型输出
   - 路径：`logs/<skill-dir>.raw.txt`
   - 含义：Codex 直接返回的原始 JSON 文本
   - 风险：可能使用了不符合 schema 的值，例如中文枚举、自由表达标签、额外字段
2. 标准化后的最终结果
   - 路径：`skills/<skill-dir>.json`
   - 含义：经过 `normalizeAndValidateScreeningResult` 校验后的正式结果
   - 作用：后续 `summary.json`、`keep_index.json`、`drop_index.json` 都基于它统计

因此，判断一次筛选是否“成功”的标准，不是 `raw.txt` 里有没有内容，而是有没有生成合法的 `skills/*.json`。

如果你想直接拿到“哪些原始 skill 被保留下来了”，应优先看：

- 单小类模式：`retained_skills/<skill-dir>/`
- 批量模式：`retained_skills/<category>__<subcategory>__<skill-dir>/`

如果你想快速浏览保留结论摘要，则看：

- `keep_index.json`
- `batch_keep_index.json`

## 输出语言约定

当前推荐且默认的正式输出语言约定是：

- JSON 字段名保持英文
- 结构化枚举值保持英文
- `capability_archetype` 保持稳定英文 slug
- 其余解释性自然语言字段使用简体中文

这里的“解释性自然语言字段”主要包括：

- `summary`
- `harbor_task_adaptation_summary`
- `skill_benefit_rationale`
- `positive_signals`
- `blocking_issues`
- `input_synthesis_feasibility.rationale`
- `container_feasibility.rationale`
- `uncertainties`
- `seed_reuse_signals`

这样设计的原因是：

- schema 和聚合逻辑依赖英文结构值
- 人读结果时又希望正文直接是中文
- `capability_archetype` 需要作为稳定标签参与聚类和统计，不适合改成自由中文短语

## 字段总览

### 身份字段

#### `category_slug`

- 含义：skill 所属的大类 slug
- 来源：由小类目录路径自动推断，不以模型原始输出为准
- 例子：如果输入目录是 `/mnt/e/skill_all/development/backend`，这里通常会是 `development`

#### `subcategory_slug`

- 含义：skill 所属的小类 slug
- 来源：由单小类输入目录或批量模式下自动发现到的小类目录推断，不以模型原始输出为准
- 例子：`backend`

#### `skill_dir`

- 含义：该 skill 的目录名
- 来源：本地目录名
- 例子：`01__acp-router`

#### `skill_id`

- 含义：去掉排序前缀后的 skill 标识
- 来源：由目录名解析得到
- 规则：如果目录名是 `01__acp-router`，则 `skill_id` 是 `acp-router`

## 主判定字段

#### `decision`

- 含义：最终保留还是丢弃该 skill
- 合法值：
  - `keep`：保留
  - `drop`：弃用
- 判断目标：这个 skill 是否值得进入后续 Harbor 造题或 seed/template 归纳流程

#### `confidence`

- 含义：模型对本次筛选结论的置信度
- 合法值：
  - `low`
  - `medium`
  - `high`
- 解读建议：
  - `high` 表示证据比较充分
  - `medium` 表示基本能判断，但仍有一定不确定性
  - `low` 表示证据不足或边界较模糊

#### `summary`

- 含义：对该 skill 是否值得保留的简短总结
- 作用：给人快速扫读；也是 `keep_index.json` 和 `drop_index.json` 中最常看的摘要字段

#### `harbor_task_adaptation_summary`

- 含义：如果要把该 skill 转成 Harbor 任务，任务大致会是什么形态，主要难点在哪里
- 重点：这里不是只说“能不能做”，而是要说明“怎么做”和“做起来会卡在哪”

#### `skill_benefit_rationale`

- 含义：解释“用了这个 skill 的 agent 为什么会比不用 skill 更强”
- 重点：要体现 skill advantage，而不是泛泛而谈“它和主题相关”

## 证据字段

#### `positive_signals`

- 含义：支持保留或说明 skill 有价值的正向信号
- 形式：字符串数组
- 常见内容：
  - 结构清晰的方法论
  - 可迁移的规则或检查框架
  - 可稳定验证的输出模式

#### `blocking_issues`

- 含义：阻碍该 skill 转成 Harbor 任务的主要问题
- 形式：字符串数组
- 常见内容：
  - 太依赖外部系统
  - 验证标准过于主观
  - 边界过宽
  - 只是运维/导航类说明

#### `input_synthesis_feasibility`

- 含义：如果本地没有现成完整资产，Codex 是否还能合理构造任务输入
- 结构：
  - `judgment`
  - `rationale`

#### `input_synthesis_feasibility.judgment`

- 含义：构造任务输入的可行性等级
- 合法值：
  - `feasible`：可行
  - `risky`：有风险
  - `not_feasible`：基本不可行

#### `input_synthesis_feasibility.rationale`

- 含义：对上面可行性判断的解释
- 重点：说明为什么可行、为什么有风险，或者为什么基本不可行

#### `container_feasibility`

- 含义：如果把该 skill 转成 Harbor 任务，该任务是否适合在 Harbor 的容器环境中运行
- 结构：
  - `judgment`
  - `rationale`
- 这是当前筛选里的显式判据，不再只是隐含在 `harbor_taskability` 里

#### `container_feasibility.judgment`

- 合法值：
  - `feasible`
  - `risky`
  - `not_feasible`
- 解读：
  - `feasible`：任务可以较自然地在 Harbor 容器里 self-contained 运行
  - `risky`：理论可做，但容器依赖、运行形态或外部条件存在明显风险
  - `not_feasible`：任务明显不适合容器化运行
- 规则：
  - 如果这里是 `not_feasible`，最终不应判 `keep`

#### `container_feasibility.rationale`

- 含义：解释为什么这个任务容器友好、存在风险，或根本不适合容器化
- 常见判断点：
  - 是否依赖宿主机特权
  - 是否依赖 GUI / 桌面交互
  - 是否依赖 systemd、内核能力、Docker-in-Docker、物理硬件
  - verifier 是否能在容器里稳定运行

#### `files_reviewed`

- 含义：本次判断实际读过的关键文件路径
- 形式：字符串数组
- 约束：应该只列真正读过的文件
- 用途：方便事后复核“结论是基于哪些证据得出的”

#### `uncertainties`

- 含义：当前结论里仍然不能确定、只能保留意见的部分
- 形式：字符串数组
- 用途：防止模型把推测说成确定事实

## 归纳与聚类字段

#### `capability_archetype`

- 含义：这个 skill 在当前小类中属于哪一种“能力原型”
- 作用：后续做小类归纳、种子模板抽象时，用它做聚类和归类
- 推荐写法：稳定、简短的小写标签
- 推荐例子：
  - `backend_patterns`
  - `validation_guardrails`
  - `agent_routing`

#### `representativeness`

- 含义：这个 skill 是否能代表当前小类的一类典型能力
- 合法值：
  - `low`
  - `medium`
  - `high`
- 解读：
  - `high` 表示很适合做该小类的代表样本
  - `low` 表示即便可用，也不太适合作为模板代表

#### `harbor_taskability`

- 含义：把该 skill 落成 Harbor 任务的整体难度和稳定性
- 合法值：
  - `low`
  - `medium`
  - `high`
- 解读：
  - `high` 表示较容易形成稳定、自包含、可验证的 Harbor 任务
  - `low` 表示很难稳定落地
- 注意：
  - `harbor_taskability` 现在不单独承担“容器可行性”的表达
  - 容器适配性由 `container_feasibility` 显式表示

#### `seed_reuse_signals`

- 含义：这个 skill 身上有哪些结构线索，未来可抽成小类级 seed/template
- 形式：字符串数组
- 常见内容：
  - 固定输入模式
  - 稳定输出模式
  - verifier pattern
  - skill benefit shape
  - 任务步骤结构

#### `drop_reason_category`

- 含义：如果最终是 `drop`，最主要的丢弃原因属于哪一类
- 规则：
  - 当 `decision=keep` 时，必须是 `not_applicable`
  - 当 `decision=drop` 时，不能是 `not_applicable`
- 合法值：
  - `not_applicable`
  - `not_verifiable`
  - `container_unfriendly`
  - `too_external`
  - `too_broad`
  - `no_skill_advantage`
  - `ops_only`
  - `insufficient_signal`
  - `unknown`

各值说明：

- `not_applicable`
  - 仅用于 `keep`
- `not_verifiable`
  - 难以设计稳定、程序化、无歧义的 verifier
- `container_unfriendly`
  - 主要问题是任务明显不适合放进 Harbor 容器环境运行
- `too_external`
  - 太依赖外部账号、外部服务、实时状态或企业内系统
- `too_broad`
  - 题目边界过宽，难以收敛成轻量 Harbor 任务
- `no_skill_advantage`
  - 即使主题相关，也体现不出“用 skill 会明显更强”
- `ops_only`
  - 主要是安装、发布、session 管理、router、导航、运维类技能
- `insufficient_signal`
  - skill 信息太少，无法支撑高质量判断
- `unknown`
  - 其他原因，或当前无法更细分

## 容器适配性的实际使用口径

当前筛选已经把“是否适合放在 Harbor 容器里跑”提升成显式标准。

你可以这样理解：

- `harbor_taskability`
  - 更偏“落成 Harbor 任务的整体难度和稳定性”
- `container_feasibility`
  - 更偏“任务运行形态本身是否容器友好”

一个 skill 可能：

- `container_feasibility = feasible`
  - 但 `harbor_taskability = medium`
  - 说明容器里能跑，但任务设计仍有一定复杂度

也可能：

- `harbor_taskability = low`
  - 且 `container_feasibility = not_feasible`
  - 说明问题已经不是“任务难”，而是“运行形态本身不适合容器”

## 你给出的样例该怎么对照理解

你发来的样例里用了很多中文值，例如：

- `decision = "弃用"`
- `confidence = "高"`
- `input_synthesis_feasibility.judgment = "有风险"`
- `representativeness = "低"`
- `harbor_taskability = "低"`
- `drop_reason_category = "仅运维类"`

从字段语义上看，它们分别大致对应：

- `"弃用"` -> `drop`
- `"高"` -> `high`
- `"有风险"` -> `risky`
- `"低"` -> `low`
- `"仅运维类"` -> `ops_only`

但需要注意：

- 这类中文值不符合当前 `skills/*.json` 的正式 schema
- 如果它们出现在 `logs/*.raw.txt` 中，我认为是正常现象
- 如果它们真的出现在 `skills/*.json` 中，我不确定，因为按当前代码它本应在 schema 校验时报错并计入 failure

另外，你样例里的：

- `category_slug = "开发"`
- `subcategory_slug = "后端"`

也不符合当前实现。按现在的目录发现逻辑，如果输入目录是 `/mnt/e/skill_all/development/backend`，正式结果里通常会被标准化成：

- `category_slug = "development"`
- `subcategory_slug = "backend"`

## 重跑与覆盖行为

这一点和看结果关系很大。

当你执行：

```bash
npm run screen -- \
  --subcategory-dir /mnt/e/skill_all/development/backend \
  --output-dir /mnt/e/skill_screening_runs/development__backend \
  --jobs 8 \
  --resume
```

其行为是：

1. `--resume` 只看 `skills/*.json` 是否存在
2. 如果某个 skill 之前失败了，但没有生成 `skills/<skill>.json`，这次仍会重新跑
3. 每次 run 结束时，`summary.json`、`keep_index.json`、`drop_index.json`、`failures.json`、`run_manifest.json` 都会被重新写一遍

日志文件的覆盖规则是：

- 如果本次仍然失败：
  - `logs/<skill>.error.txt` 会被新的失败信息覆盖
  - `logs/<skill>.prompt.md` 会被覆盖
  - 若有原始响应，`logs/<skill>.raw.txt` 会被覆盖
- 如果这次成功了：
  - `skills/<skill>.json` 会新写入
  - `logs/<skill>.prompt.md` 会被覆盖
  - `logs/<skill>.raw.txt` 会被覆盖
  - 但旧的 `logs/<skill>.error.txt` 不会被自动删除

这意味着：

- 同一个 skill 可能已经成功了，但目录里还残留上一次失败时留下的 `error.txt`
- 因此判断最终状态时，应优先看 `skills/*.json` 和本轮 `summary.json` / `failures.json`

如果你想得到完全干净的一轮输出，最稳妥的方法是：

- 使用一个全新的 `--output-dir`

我不建议在不确认后果的情况下直接用 `--overwrite`，因为当前实现会在启动时删除整个旧输出目录。

批量模式下同理，只是作用范围会扩大到整个批量输出根目录。例如：

```bash
npm run screen -- \
  --input-dir /mnt/e/skill_all/development \
  --output-dir /mnt/e/skill_screening_runs/development \
  --resume
```

这时：

- 每个小类都会写到自己的子目录，例如 `development__backend/`
- `--resume` 仍然只看各自子目录里的 `skills/*.json`
- 批量根目录下的 `batch_summary.json`、`batch_keep_index.json`、`batch_drop_index.json`、`batch_failures.json`、`batch_manifest.json` 会在本轮结束后整体重写
- 如果使用 `--overwrite`，删除的是整个批量输出根目录，而不只是某一个小类子目录
