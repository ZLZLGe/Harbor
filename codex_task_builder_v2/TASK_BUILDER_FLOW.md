# codex_task_builder_v2 造任务流程说明

本文基于当前 `codex_task_builder_v2` 源码整理，目标是把这个项目“如何从 source task 自动构造 Harbor task family”讲清楚，方便后续维护、排障和改 prompt/validator。

## 1. 项目目标

`codex_task_builder_v2` 不是一个单纯的“任务生成器”，而是一条闭环流水线：

`planner -> writer -> reviewer -> static validate -> Harbor Oracle runtime -> repair -> publish/quarantine`

核心目标有两个：

1. 自动从已有 source task 构造新的 Harbor task family。
2. 不只生成草稿，还要自动做审稿、静态校验、Oracle 运行和失败修复。

---

## 2. 关键目录

默认目录约定如下：

- source tasks：`/home/levi/Harbor/tasks_library/skillsbench/tasks`
- raw runs：`/home/levi/Harbor/codex_task_builder_v2_runs/raw`
- quarantine：`/home/levi/Harbor/codex_task_builder_v2_runs/quarantine`
- final tasks：`/home/levi/Harbor/tasks_library/auto_harbor_tasks`

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

---

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
  - 程序会把 planner 的任务数组映射成 `similar1`、`transfer1` 这种固定 ID

---

## 4. CLI 入口

CLI 支持四类命令：

- `inventory`
- `generate-family`
- `batch`
- `review`

### 4.1 inventory

只扫描 source tasks，不生成任务。输出：

- source task id
- difficulty / category
- skill names
- environment 资产列表

### 4.2 generate-family

面向单个 source task 或单个 generation unit 生成 family。

### 4.3 batch

批量处理多个 source tasks / generation units。和 `generate-family` 共用同一套生成逻辑，只是外层可以并发。

### 4.4 review

不重新生成任务，只会找到最近一次 raw workspace，然后重新跑 reviewer。

---

## 5. 完整造任务流程

下面按实际执行顺序说明。

### 第 1 步：发现 source task

程序先从 `source-root` 扫描 source tasks，读取：

- `task.toml`
- `instruction.md`
- `environment/skills/*/SKILL.md`

并解析出：

- task metadata
- skills 列表

### 第 2 步：构造 generation units

程序根据 `--skill-mode`、`--similar-count`、`--transfer-count` 生成 `GenerationUnit`：

- `all` 模式：每个 source task 一个 unit
- `per-skill` 模式：每个 source task 的每个 skill 一个 unit

### 第 3 步：读取已发布 family，决定缺哪些槽位

程序会读取 `final-root/<source-task-id>/<scope>/` 下已经发布的任务：

- 识别已有的 `similarN`
- 识别已有的 `transferN`

然后只补缺失槽位。

例如目标是：

- `similar-count = 2`
- `transfer-count = 3`

如果 final 里已经有：

- `similar1`
- `transfer1`

那么本轮只需要补：

- `similar2`
- `transfer2`
- `transfer3`

这一步的目的是避免重复造已经发布的任务。

### 第 4 步：runtime preflight

在真正生成之前，程序先检查运行环境：

- 是否能找到 `harbor`
- `harbor --version` 是否正常
- 如果 runtime 环境是 `daytona`
  - 是否设置了 `DAYTONA_API_KEY`
- 如果 runtime 环境是 `docker`
  - 是否存在 `docker`
  - `docker info` 是否正常

preflight 失败会直接终止，不进入生成阶段。

### 第 5 步：创建 family workspace

每个 unit 会创建一个独立 workspace：

```text
<raw-root>/<run-id>/<source-task-id>/<scope>/
```

其中固定包含：

- `source_task/`
- `builder_refs/harbor/`
- `drafts/`
- `artifacts/`
- `TASK_BUILDER_BRIEF.md`

说明：

- `source_task/` 是本轮 source task 的工作副本
- `builder_refs/harbor/` 是 Harbor builder 参考资料
- `drafts/` 是本轮派生任务草稿
- `artifacts/` 存 planner/writer/reviewer/runtime/repair 的输出
- `TASK_BUILDER_BRIEF.md` 是给 Codex 的统一总纲

在 `per-skill` 模式下，复制 `source_task/` 时只保留当前目标 skill，不会把其他 skills 一并带入。

### 第 6 步：planner 生成 family 蓝图

程序调用 Codex planner，要求它：

- 先读 `TASK_BUILDER_BRIEF.md`
- 再读 `source_task/`
- 再读 `builder_refs/harbor/`
- 如有已发布任务，也必须读 final-root 里的历史任务

planner 只做“family 规划”，不直接写文件。

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

如果 planner 阶段有 blocking issue，整组 family 会直接失败。

### 第 7 步：writer 生成每个 draft task

对于每个 `DerivedTaskPlan`：

1. 程序先创建 `drafts/<task-id>/`
2. 预先复制当前 scope 对应的 `environment/skills/`
3. 写入 `plan.json`
4. 调用 writer prompt，让 Codex 生成完整 Harbor 任务

writer 需要产出的核心文件是：

- `task.toml`
- `instruction.md`
- `environment/Dockerfile`
- `environment/` 下必要输入资产
- `solution/solve.sh`
- `tests/test.sh`
- `tests/test_outputs.py`
- `plan.json`

writer prompt 会特别强调：

- 要读取 sibling drafts，避免本轮内部撞题
- 要读取 final-root 中已发布任务，避免和历史任务撞题
- `instruction.md` 和 task metadata 必须是英文
- `environment/Dockerfile` 必须保留 `COPY skills /root/.codex/skills`
- 参考解和 verifier 不能直接依赖 skill runtime

### 第 8 步：reviewer 审稿

writer 完成后，程序进入 cycle 循环。每一轮 cycle 的第一步是 reviewer。

reviewer 是 family 级别的，它会同时审查：

- `TASK_BUILDER_BRIEF.md`
- `source_task/`
- `builder_refs/harbor/`
- 当前全部 `drafts/`
- final-root 中同 family 已发布任务

reviewer 的输出分两部分：

- `taskResults`
  - 针对每个任务给出：
    - `pass`
    - `issues`
    - `visibilityPass`
    - `skillBenefitPass`
    - `testabilityPass`
- `familyObservations`
  - 针对整个 family 的多样性、布局等给出意见

程序不会盲信 reviewer，会做结果归一化和结构校验，防止模型：

- 漏字段
- 任务 ID 对不上
- 返回未知任务
- 把 `familyObservations` 返回成错误结构

### 第 9 步：static validate

对每个 draft task，会做静态校验。

静态校验主要包括：

1. 必备文件是否存在
   - `plan.json`
   - `task.toml`
   - `instruction.md`
   - `environment/Dockerfile`
   - `solution/solve.sh`
   - `tests/test.sh`
   - `tests/test_outputs.py`

2. `plan.json` 是否与目录名一致

3. `environment/skills` 是否与当前 scope 严格一致
   - `per-skill`：必须且只能有当前目标 skill
   - `all`：必须等于 source task 的全部 skills

4. `task.toml` metadata 是否正确
   - `id`
   - `name`
   - `description`
   - `primary_output_file`
   - `source_task_id`
   - `task_role`
   - `tags`

5. 英文约束
   - `instruction.md` 不得含中文
   - `metadata.name` / `metadata.description` 不得含中文

6. 固定资源配额
   - `cpus = 2`
   - `memory_mb = 2048`
   - `storage_mb = 5120`
   - `gpus = 0`

7. Dockerfile 基础镜像策略
   - 不能使用本地/私有 registry
   - 必须保留 `COPY skills /root/.codex/skills`

8. skill runtime 耦合检查
   - `solution/solve.sh`
   - `tests/test.sh`
   - `tests/test_outputs.py`

如果这些文件直接引用：

- `environment/skills/**`
- `/root/.codex/skills/**`
- `/app/skills/**`
- 或通过 `sys.path` / `PYTHONPATH` 注入 skills 目录

就会被判定为“参考解 / verifier 硬依赖 skill”，直接报 static issue。

这条规则的目的是保证：

- 参考解和验收器与 shipped skill 解耦
- 在“装 skill”和“不装 skill”两种评测设置下，reference solution 与 verifier 都能独立跑通

### 第 10 步：runtime validate（Harbor Oracle）

只有 reviewer 和 static 都通过的任务，才会进入 runtime validate。

runtime validate 的执行命令是：

```bash
harbor run -p <task_dir> -a oracle -e <daytona|docker> --force-build --jobs-dir <logs_dir> --job-name <job_name>
```

每次 runtime 尝试都有唯一目录：

```text
artifacts/runtime/<task-id>/cycle-<cycle>-attempt-<attempt>/
```

这是为了避免 repair 后复用旧结果。

runtime 阶段会收集这些证据：

- `harbor-run.log`
- `job.log`
- `trial.log`
- `verifier/test-stdout.txt`
- `reward.txt` 或 `reward.json`
- `result.json`
- `artifacts/manifest.json`
- `log-index.json`

通过标准如下：

1. 必须产出可解析的 `result.json`
2. `result.json` 里不能有 `exception_info`
3. verifier 必须产出 reward
4. reward 必须 `>= 1.0`
5. `harbor run` 自身退出码必须为 0

只要任意一条失败，就会生成 runtime issue。

### 第 11 步：repair

如果某个任务在以下任一阶段失败：

- reviewer
- static validate
- runtime validate

并且还没超过 `maxRepairRounds`，程序就会触发 repair。

repair 不只是给 Codex 一句“失败了”，而是把完整证据喂回去，包括：

- reviewer issues
- static issues
- runtime issues
- `runtimeDir`
- `log-index.json`
- `harbor-run.log`
- `job.log`
- `trial.log`
- `verifier/test-stdout.txt`
- `reward.txt/reward.json`
- `result.json`
- `artifacts/manifest.json`

repair 会：

- 尽量最小化修改
- 继续使用同一个 repair thread
- 修完后进入下一轮 reviewer/static/runtime

直到：

- 全部通过，或
- 没有 repair 额度了，或
- 本轮没有新的修复动作

### 第 12 步：发布或隔离

循环结束后，每个任务只有两种去向：

- `passed = true`
  - 复制到 `final-root`
- `passed = false`
  - 复制到 `quarantine-root`

发布不是整个草稿目录原样搬走，而是 allowlist 复制，只保留 Harbor 必需文件：

- `task.toml`
- `instruction.md`
- `plan.json`
- `environment/`
- `solution/`
- `tests/`

不会执行删除操作。

如果目标目录已经存在，会标记为 `existing`，不会强制覆盖。

---

## 6. 日志与产物

### 6.1 workspace 内产物

每个 family workspace 下至少包含：

- `TASK_BUILDER_BRIEF.md`
- `source_task/`
- `builder_refs/harbor/`
- `drafts/`
- `artifacts/`

### 6.2 artifacts 内常见文件

- `generation-unit.json`
- `family-plan.json`
- `family-plan.raw.json`
- `<task-id>.writer.json`
- `<task-id>.writer.raw.json`
- `review-result.round-<n>.json`
- `review-result.round-<n>.raw.json`
- `<task-id>.runtime.cycle-<n>.json`
- `<task-id>.repair.<n>.json`

### 6.3 runs 根目录

整个项目级别还会持续写：

- `codex_task_builder_v2_runs/manifest.jsonl`
- `codex_task_builder_v2_runs/<run-id>.json`

前者是 phase 级流水日志，后者是 run summary。

---

## 7. 当前这套流程最重要的约束

### 7.1 任务命名固定

程序不会接受任意 task id，最终一定映射为：

- `similar1`, `similar2`, ...
- `transfer1`, `transfer2`, ...

### 7.2 final-root 是一等输入

planner / writer / reviewer 都必须读取已发布任务，用于：

- 避免撞题
- 只补齐缺失槽位

### 7.3 用户可见文本必须是英文

至少包括：

- `instruction.md`
- `task.toml` 中的 `metadata.name`
- `task.toml` 中的 `metadata.description`

### 7.4 shipped skill 只服务 agent，不服务 oracle

这是当前版本特别重要的规则：

- shipped skill 可以帮助 agent 解题
- 但 `solution/solve.sh` 和 verifier 不能把 skill 当成直接运行时依赖

否则就无法公平比较：

- 添加 skill 的 agent
- 不添加 skill 的 agent

在相同任务上的真实效果差异

### 7.5 runtime 失败统一进 repair

当前实现不再区分：

- infra retry
- repair retry

而是每个 cycle 每个任务只跑一次 runtime，失败后统一进入 repair 流。

---

## 8. 一句话总结

`codex_task_builder_v2` 的本质不是“让模型写几个 Harbor 任务”，而是：

**先把 source task 按 scope 拆成 family，再让 Codex 基于 source task、Harbor 参考材料和已发布任务做规划与写作，随后用 reviewer + static validate + Harbor Oracle runtime 把任务往可发布状态收敛，最后把通过的任务发布到 final-root，把失败的任务隔离到 quarantine-root。**

这套设计的重点不在“生成”，而在“自动收口”。
