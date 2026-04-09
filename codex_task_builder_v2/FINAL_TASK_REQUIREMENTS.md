# codex_task_builder_v2 最终生成任务要求

本文整理当前 `codex_task_builder_v2` 对“最终生成 Harbor 任务”的要求，目标是把分散在 `prompts.ts`、`validate.ts`、Harbor oracle/runtime 和现有流程文档中的约束汇总成一份可直接对照的规范。

建议把这些要求分成两层理解：

- `必须满足`
  - 当前代码会通过 static validate、reviewer、Harbor Oracle runtime 或发布流程实际卡住的要求。
  - 当前 builder 默认 runtime/oracle 后端是 `e2b`，也允许切换到 `daytona` 或 `docker`。
- `应该满足`
  - 当前主要通过 prompt 和 reviewer 强化的质量要求。
  - 这类要求不一定全都有硬编码校验，但都属于当前 builder 希望稳定产出的任务形态。

## 1. 最终产物定位

最终生成的内容必须是一个完整、可发布的 Harbor task，而不是草稿片段、仅有测试的半成品，或只能靠 builder 上下文才能运行的内部中间产物。

最终任务应同时满足：

- 是一个自包含的 Harbor task
- 能在 Harbor 中完成 build / start / verify
- 用户可见文本使用英文
- 有清晰输出契约
- 有稳定 verifier
- 有 shipped skill 时，skill 对解题应有真实帮助

## 2. 目录与命名要求

最终发布目录结构固定为：

```text
<final-root>/<source-task-id>/<scope>/<task-name>
```

其中：

- `scope`
  - `all` 模式固定为 `all-skills`
  - `per-skill` 模式固定为目标 skill 的 `dirName`
- `task-name`
  - 只能是 `similar1`、`similar2`、`transfer1`、`transfer2` 这类 canonical name

family 层要求：

- `similar` / `transfer` 的数量必须与本轮目标一致
- 同一 family 内的 `primaryOutputFile` 必须唯一
- 同一 family 内部任务之间应在任务场景、输入资产、输出语义和验证方式上拉开差异
- 不得与 final-root 中已发布的同 family 历史任务过于接近

## 3. 必备文件要求

每个最终任务至少必须包含：

- `plan.json`
- `task.toml`
- `instruction.md`
- `environment/Dockerfile`
- `environment/skills/**`
- `solution/solve.sh`
- `tests/test.sh`
- `tests/test_outputs.py`

补充要求：

- `plan.json` 必须保留，不能删除或改名
- 发布时只允许复制 Harbor 必需文件，不发布 builder 内部额外产物

## 4. task.toml 与基础元数据要求

`task.toml` 中的 `[metadata]` 至少必须包含：

- `id`
- `name`
- `description`
- `author_name`
- `author_email`
- `difficulty`
- `category`
- `tags`
- `primary_output_file`
- `source_task_id`
- `task_role`

并且必须满足：

- `metadata.id` 必须等于当前 `derivedTaskId`
- `metadata.name` 必须显式包含 `Similar N` 或 `Transfer N`
- `metadata.name` 与 `metadata.description` 必须使用英文
- `metadata.primary_output_file` 必须与 `plan.json` 一致
- `metadata.source_task_id` 必须与 source task 一致
- `metadata.task_role` 必须与任务角色一致
- `tags` 不能为空

`[environment]` 必须固定为：

```toml
[environment]
cpus = 2
memory_mb = 2048
storage_mb = 5120
gpus = 0
```

## 5. 文本与指令要求

以下用户可见文本必须使用英文：

- `instruction.md`
- `task.toml` 中的 `metadata.name`
- `task.toml` 中的 `metadata.description`

`instruction.md` 应满足：

- 清楚说明任务目标、输入资产、输出契约、边界条件
- 不直接点名当前 shipped skill 的 `name` 或 `dirName`
- 不引入隐藏要求
- 不把任务写成按步骤执行即可过关的教程式 recipe
- 不依赖 source task 之外的隐含背景知识

## 6. skill scope 与 skill 使用要求

`environment/skills` 必须与当前 scope 精确一致：

- `per-skill`
  - 必须且只能包含当前目标 skill
- `all`
  - 必须与 source task 中全部 shipped skills 一致

并且必须满足：

- 任务只能依赖当前 scope 下可见的 shipped skills
- 不得假设其他未提供 skills 存在
- 参考解与 verifier 不能把 skill 当运行时依赖
- shipped skill 的作用是帮助 agent 解题，不是给 `solution/solve.sh` 或 `tests/**` 直接调用

## 7. Dockerfile 要求

`environment/Dockerfile` 必须满足：

- 必须显式声明 `WORKDIR`
- 默认优先 `WORKDIR /root`
- 必须保留 `COPY skills /root/.codex/skills`
- 不得使用 `COPY . /root`、`ADD . /root` 或同类宽泛复制
- 不得把 `skills` 复制到普通运行时路径，如：
  - `/root/environment/skills`
  - `/app/skills`
  - `/workspace/skills`
- 不得使用私有、本地、仅在个人机器可用的 registry
- 必须使用公开可复现的公共镜像，或 `FROM scratch`

## 8. solution / verifier / runtime 契约要求

当前 runtime/oracle 口径：

- 当前 builder 默认使用 Harbor oracle + `e2b` 做 runtime 校验。
- 也允许切换到 `daytona` 或 `docker`。
- 最终任务不应依赖只在某一个特定 runtime 后端下才成立的私有假设；应在 Harbor 官方 oracle/runtime 语义下稳定 build / start / verify。

`solution/solve.sh` 要求：

- 是参考解脚本，而不是现成答案搬运器
- 不得只是复制、重命名、移动、直接输出随任务提供的完整标准答案
- 与 `tests/test.sh`、`tests/test_outputs.py`、`environment/Dockerfile` 的路径契约必须一致

`tests/test_outputs.py` 要求：

- 只检查 `instruction.md` 明示的输出契约
- 尽量面向结果语义，而非内部实现细节
- `expected` 应来自输入资产、题目规则或可复算逻辑
- 不得依赖任务内现成答案文件
- 不能让 fresh state、no-op、复制现成答案、改名已有 deliverable 这类伪解法错误通过

`tests/test.sh` 要求：

- 必须先创建 `/logs/verifier`
- 必须稳定写出 `reward.txt` 或 `reward.json`
- 不能只是裸跑测试命令然后直接退出
- 即使测试失败，也必须在退出前落盘 reward

运行通过标准：

- 必须产出可解析的 `result.json`
- `result.json` 里不能有 `exception_info`
- verifier 必须产出 reward
- reward 必须 `>= 1.0`
- `harbor run` 自身退出码必须为 `0`

## 9. benchmark 质量要求

### 9.1 难度要求

无论 `all` 模式还是 `per-skill` 模式，benchmark 任务默认都应规划为 `hard`。

只有在下面这种情况下，才允许降到 `medium`：

- `hard` 带来的主要代价会变成 build/start/runtime 噪声
- 难点不再体现为 skill bottleneck
- 继续追求 `hard` 只会明显破坏评测稳定性

不应为了追求“hard”而引入：

- 重型环境搭建
- 多服务长启动链路
- 大下载、大模型预热
- 明显脆弱的时序依赖
- 主要依赖运行基础设施而非任务本身的难点

### 9.2 skill effect 要求

任务应该尽量体现“带相关 skill 时能明显压缩搜索空间，不带相关 skill 时更容易走错路、漏关键步骤或选错工具”的特征。

更具体地说：

- `per-skill`
  - 当前目标 skill 必须是关键瓶颈，而不是可有可无的加速器
- `all`
  - 多个 shipped skills 的核心收益点必须真实参与解题，不能退化成只靠通用能力也能直接完成的任务

不应生成以下弱信号任务：

- 单个明显文件就能直接读出答案
- 单条 shell 命令就能直接完成
- 主要依赖浅层通用 bash/python/jq/grep 技巧
- skill 只是节省几分钟体力，而不是改变解题成败

### 9.3 hard to solve but easy to verify

任务应满足：

- 难点在求解，不在猜 verifier
- 验收规则清晰、可程序化判断
- 输出格式、路径、字段、容忍误差应明确
- 不靠隐藏阈值、隐藏步骤、隐藏接口卡 agent

### 9.4 self-contained

任务必须 self-contained：

- 完成任务所需关键信息必须写在 `instruction.md` 或提供的输入资产中
- 不依赖额外口头说明、私人背景知识或 builder 内部上下文

## 10. 明确禁止的坏任务形态

以下情况都应视为不合格：

- 机械复写 source task，只做轻微换皮
- 与同 family 已发布任务几乎重复
- 中文 instruction 或中文 metadata
- solution / verifier 直接引用 skill 安装路径或 skill 模块
- instruction 接近完整解法教程
- 存在一眼可见的 answer-like 文件
- 可以通过复制、改名、搬运现成 deliverable 直接过关
- 任务主要是工程体力活，不是 skill 带来的关键能力
- 任务虽然标了 skill，但不用相关 skill 通用 agent 也大概率能直接完成
- 为了修 runtime 问题而把任务稀释成 easy 或普通 medium 小题

## 11. 发布口径

一个任务只有两种最终去向：

- `passed = true`
  - 发布到 `final-root`
- `passed = false`
  - 进入 `quarantine-root`

因此，能进入最终发布目录的任务，至少应同时通过：

- reviewer 审稿
- static validate
- Harbor Oracle runtime
  - 当前默认后端是 `e2b`

如果一个任务只能靠降低难度、暴露关键线索、增加教程式步骤，或放宽 verifier 才能通过，那么它不应被视为合格的最终 benchmark 任务。
