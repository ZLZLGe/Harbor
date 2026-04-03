# codex_task_builder_v2_no_repair 造任务流程说明

本文基于当前 `codex_task_builder_v2_no_repair` 源码整理，目标是把“如何从 source task 自动构造 Harbor task family”讲清楚，方便后续做对照实验、排障和迭代 prompt。

这个版本和 `codex_task_builder_v2` 的核心区别只有一条：

- 保留 planner、writer、reviewer、static validate、runtime validate、publish/quarantine
- 完全移除 repair
- 任一任务在 reviewer、static validate、runtime validate 阶段失败后，都直接进入 quarantine

## 1. 总体执行链

完整流程是：

`planner -> writer -> reviewer -> static validate -> Harbor Oracle runtime -> publish/quarantine`

注意：

- 这里只会跑一轮固定 cycle
- 代码里仍然保留 `round-0`、`cycle-0` 这类命名，只是为了和原版产物结构保持兼容

## 2. 默认目录

- source tasks：`/home/levi/Harbor/tasks_library/skillsbench/tasks`
- raw runs：`/home/levi/Harbor/codex_task_builder_v2_no_repair_runs/raw`
- quarantine：`/home/levi/Harbor/codex_task_builder_v2_no_repair_runs/quarantine`
- final tasks：`/home/levi/Harbor/tasks_library/auto_harbor_tasks_v2_no_repair`

最终发布目录结构固定为：

```text
<final-root>/<source-task-id>/<scope>/<task-name>
```

其中：

- `scope`
  - `all-skills`：`all` 模式
  - `<skill-dir>`：`per-skill` 模式
- `task-name`
  - `similar1`, `similar2`, ...
  - `transfer1`, `transfer2`, ...

## 3. 核心数据模型

### 3.1 SourceTask

表示一个源任务，包含：

- `task.toml`
- `instruction.md`
- `environment/`
- `solution/`
- `tests/`
- `environment/skills/`
- 从 `task.toml` 解析出的 metadata
- 从 `environment/skills/*/SKILL.md` 解析出的 shipped skills

### 3.2 GenerationUnit

实际执行单元是 `GenerationUnit`，可以理解为：

- 一个 source task
- 加上一个 scope

两种 scope 模式：

- `all`
  - 一个 source task 只生成一个 family
  - 保留全部 shipped skills
  - scope 固定为 `all-skills`
- `per-skill`
  - 一个 source task 会按 skill 拆成多个 family
  - 每个 family 只围绕一个目标 skill
  - scope 等于该 skill 的 `dirName`

### 3.3 FamilyPlan / DerivedTaskPlan

- `FamilyPlan`
  - planner 输出的 family 级蓝图
  - 描述本轮应生成多少个 `similar` / `transfer`
- `DerivedTaskPlan`
  - 把 `FamilyPlan` 展平后的单任务蓝图
  - 程序会把 planner 给出的任务映射为固定 ID，例如 `similar1`、`transfer1`

## 4. CLI 命令

CLI 支持四类命令：

- `inventory`
- `generate-family`
- `batch`
- `review`

说明：

- `inventory` 只扫描 source tasks，不生成任务
- `generate-family` 和 `batch` 共用同一套生成逻辑
- `review` 不重新写任务，只会拿最近一次 raw workspace 重跑 reviewer

## 5. 详细执行步骤

### 第 1 步：发现 source task

程序先从 `source-root` 扫描 source tasks，读取：

- `task.toml`
- `instruction.md`
- `environment/skills/*/SKILL.md`

并解析出：

- task metadata
- skills 列表

### 第 2 步：构造 generation units

程序根据 `--skill-mode`、`--similar-count`、`--transfer-count` 构造 `GenerationUnit`：

- `all` 模式：每个 source task 一个 unit
- `per-skill` 模式：每个 source task 的每个 skill 一个 unit

如果传了 `--target-skill-dir`，会在这里继续过滤，只保留目标 skill 对应的 unit。

### 第 3 步：读取已发布 family，判断还缺哪些槽位

程序会扫描 `final-root/<source-task-id>/<scope>/` 下已经发布的任务：

- 识别已有的 `similarN`
- 识别已有的 `transferN`

然后只补缺失槽位。

例如目标是：

- `similar-count = 2`
- `transfer-count = 3`

如果 final 里已经有：

- `similar1`
- `transfer1`

那么本轮只会继续补：

- `similar2`
- `transfer2`
- `transfer3`

这样可以避免重复生成已经发布的任务。

### 第 4 步：runtime preflight

真正开始生成之前，程序先检查运行环境：

- 是否能找到 `harbor`
- `harbor --version` 是否正常
- 如果 runtime 环境是 `daytona`
  - 是否设置了 `DAYTONA_API_KEY`
- 如果 runtime 环境是 `docker`
  - 是否存在 `docker`
  - `docker info` 是否正常

preflight 失败会直接终止，不进入生成阶段。

### 第 5 步：创建 family workspace

每个 unit 都会创建一个独立 workspace：

```text
<raw-root>/<run-id>/<source-task-id>/<scope>/
```

固定包含：

- `source_task/`
- `builder_refs/harbor/`
- `drafts/`
- `artifacts/`
- `TASK_BUILDER_BRIEF.md`

说明：

- `source_task/` 是本轮 source task 的工作副本
- `builder_refs/harbor/` 是 Harbor builder 参考资料
- `drafts/` 是本轮派生任务草稿
- `artifacts/` 存 planner、writer、reviewer、runtime 的输出
- `TASK_BUILDER_BRIEF.md` 是给 Codex 的统一总纲

在 `per-skill` 模式下，复制 `source_task/` 时只保留当前目标 skill，不会把其他 skills 一起带进来。

### 第 6 步：planner 生成 family 蓝图

程序调用 Codex planner，要求它：

- 先读 `TASK_BUILDER_BRIEF.md`
- 再读 `source_task/`
- 再读 `builder_refs/harbor/`
- 如有已发布任务，也读取 final-root 里的历史任务

planner 只负责 family 规划，不直接写文件。

planner 的输出是严格 JSON，核心字段包括：

- `familyTheme`
- `similarTasks`
- `transferTasks`
- 每个任务的：
  - `title`
  - `goal`
  - `primaryOutputFile`
  - `difficulty`
  - `category`
  - `skillBenefitRationale`

随后程序会做三类校验：

1. `validateFamilyPlan`
   - sourceTaskId 是否一致
   - skillMode 是否一致
   - similar / transfer 数量是否一致
2. `validateTaskPlans`
   - `derivedTaskId` 是否符合 `similarN/transferN`
   - `roleOrdinal` 是否正确
   - `primaryOutputFile` 是否唯一
3. `collectFamilyObservationIssues`
   - family 角色布局是否正确

如果 planner 阶段有 blocking issue，整组 family 会直接失败，不会进入 writer。

### 第 7 步：writer 生成每个 draft task

对每个 `DerivedTaskPlan`，程序都会：

1. 创建 `drafts/<task-id>/`
2. 预先复制当前 scope 对应的 `environment/skills/`
3. 写入 `plan.json`
4. 调用 writer prompt，让 Codex 生成完整 Harbor 任务

writer 需要产出的核心文件包括：

- `task.toml`
- `instruction.md`
- `solution/solve.sh`
- `tests/test.sh`
- 其它任务所需资源

writer 产物会同时记录到：

- `drafts/<task-id>/`
- `artifacts/<task-id>.writer.json`
- `artifacts/<task-id>.writer.raw.json`

### 第 8 步：reviewer 做 family 级审稿

writer 全部完成后，程序只会做一次 reviewer：

- 调用 `reviewFamily(...)`
- 输出落到：
  - `artifacts/review-result.round-0.json`
  - `artifacts/review-result.round-0.raw.json`

reviewer 会返回两类信息：

- `taskResults`
  - 每个任务是否通过
  - 每个任务的问题列表
- `familyObservations`
  - family 级别的问题，例如多样性不足、角色布局异常

随后程序会把 reviewer 的结果归并到每个任务的 `TaskCycleState` 中。

### 第 9 步：static validate

每个任务都会继续做静态校验，主要检查：

- `plan.json` 是否存在且和当前蓝图一致
- `task.toml` metadata 是否合法
- instruction 与 metadata 的英文约束
- `environment/skills` 是否和当前 scope 精确一致
- Dockerfile 是否符合 builder 规则
- Harbor 任务目录结构是否完整

此时每个任务会得到两类前置问题：

- reviewer issues
- static issues

程序会把这些问题写进 manifest。

如果一个任务在这里已经有问题：

- 不会进入 runtime
- 不会尝试修复
- 最终会直接复制到 quarantine

### 第 10 步：runtime validate

只有 reviewer 和 static validate 都通过的任务，才会进入 runtime。

当前实现固定只跑一次：

- `cycle = 0`
- `attempt = 1`

运行时会调用 Harbor Oracle，例如：

```bash
harbor run -p <task_dir> -a oracle -e daytona --force-build --jobs-dir <logs_dir> --job-name <job_name>
```

runtime 证据会写入：

- `artifacts/<task-id>.runtime.cycle-0.attempt-1.json`
- `artifacts/<task-id>.runtime.cycle-0.json`
- 对应的 runtime 日志目录

如果 runtime 通过：

- `taskState.passed = true`

如果 runtime 失败：

- 记录 `runtimeIssues`
- 记录运行证据
- 不会进入 repair
- 最终直接进入 quarantine

### 第 11 步：publish 或 quarantine

全部任务处理完后，程序按每个任务的最终状态分流：

- 通过 runtime 的任务：复制到 `final-root`
- 其它任务：复制到 `quarantine-root`

这里不会回写修改旧任务，也不会删除旧任务，只会把当前 draft 的必要文件复制到目标目录。

最终会写出 run summary，里面包含：

- `publishedTaskIds`
- `quarantinedTaskIds`
- `familyObservationIssues`
- `issues`
- `finalDirs`
- `quarantineDirs`

## 6. 单轮基线的实际含义

这个 no-repair 版本的实验语义是：

- planner 负责 family 级设计
- writer 直接产出可运行任务
- reviewer / static / runtime 只负责判定是否合格
- 一旦失败，就保留失败样本，不再让 Codex二次修改

所以它更适合做这些对照：

- 有 repair 和无 repair 的最终发布率差异
- 有 repair 和无 repair 的 Oracle 通过率差异
- 有 repair 和无 repair 的失败类型分布差异

## 7. 常见产物位置

以某个 family 为例：

```text
<raw-root>/<run-id>/<source-task-id>/<scope>/
```

你通常会关心这些文件：

- `TASK_BUILDER_BRIEF.md`
- `source_task/`
- `builder_refs/harbor/`
- `drafts/<task-id>/`
- `artifacts/family-plan.json`
- `artifacts/<task-id>.writer.json`
- `artifacts/review-result.round-0.json`
- `artifacts/<task-id>.runtime.cycle-0.json`
- `summary.json`

发布目录：

```text
<final-root>/<source-task-id>/<scope>/<task-id>/
```

隔离目录：

```text
<quarantine-root>/<source-task-id>/<scope>/<task-id>/
```

## 8. 和原版 v2 的区别

和 `codex_task_builder_v2` 相比，这个目录只做了这些语义变化：

- 删除 repair prompt
- 删除 repair structured output schema
- 删除 `repairTask(...)`
- 删除 `--max-repair-rounds`
- 删除多轮 cycle / repair thread 逻辑
- reviewer/static/runtime 失败直接 quarantine

其余部分尽量保持一致：

- source task 发现逻辑
- `all` / `per-skill` 作用域
- planner / writer / reviewer 提示结构
- static validate
- Harbor Oracle runtime validate
- publish / quarantine 落盘方式
- 默认产物目录层级
