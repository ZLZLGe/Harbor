# 基于 Codex SDK 的 `integrated_tasks` 批量生成器实现方案

## Summary

- 新建一个独立的 Node/TypeScript 工具 `codex_task_builder/`，不参考、不导入任何 `harbor_skill_pipeline` 内容。
- 每次生成时，把一个完整 source task 目录复制到临时工作区，然后把这个临时目录作为 Codex SDK 的 `workingDirectory`。
- Codex 在这个工作区里自由读取整个 source task：`task.toml`、`instruction.md`、`environment/**`、`environment/skills/**`、`solution/**`、`tests/**`。
- prompt 只负责控制生成方向，不负责承载 source task 内容。
- 每个 source task 固定生成 4 个全新派生任务，最终发布到 `tasks_library/integrated_tasks/<source_task_id>/<derived_task_id>/`。
- `instruction.md` 应尽量避免直接明示技能或具体 skill 名称，但要以 source task 自身的 `instruction.md` 为基线判断；如果 source task 已经显式写出技术名，派生任务沿用同等级别表述不算越界。技能文件正常保留在 `environment/skills/**` 里，是否越界由 reviewer 做语义审查。
- 同一 scratch workspace 内，后续 `task writer thread` 会直接检查 `drafts/` 下已经生成好的 sibling tasks，并尽量避免与它们在任务场景、输入资产、输出目标和测试方式上重复；这属于 prompt 级软约束，不回看更早的 `integrated_tasks/` 或 `manifest`。

## Key Changes

### 1. 新建独立工程

在仓库根目录新增 `codex_task_builder/`，包含：

- `package.json`
- `tsconfig.json`
- `src/cli.ts`
- `src/workspace.ts`
- `src/codex.ts`
- `src/prompts.ts`
- `src/schema.ts`
- `src/materialize.ts`
- `src/validate.ts`
- `src/manifest.ts`
- `src/utils.ts`

依赖固定为：

- `@openai/codex-sdk`
- `zod`
- `tsx`
- `typescript`

### 2. 工作区模型

`src/workspace.ts` 负责创建 scratch workspace。

输入源目录：

```text
/home/levi/Harbor/tasks_library/skillsbench/tasks/<source_task_id>
```

每次 run 创建：

```text
/home/levi/Harbor/codex_task_builder_runs/scratch/<run_id>/<source_task_id>/
  source_task/
  drafts/
  artifacts/
```

规则：

- 把完整 source task 原样复制到 `source_task/`
- 不裁剪 `task.toml`、`instruction.md`、`environment/**`、`environment/skills/**`、`solution/**`、`tests/**`
- 额外生成一个只给 Codex 看的 `TASK_BUILDER_BRIEF.md`，用于写死生成约束

### 3. Codex SDK 使用方式

`src/codex.ts` 负责封装 Codex SDK。

固定策略：

- 使用 `new Codex()`
- 为每个 source task 创建独立 thread
- `workingDirectory` 指向 scratch workspace 根目录
- Codex 自由读取 `source_task/` 下的所有文件
- 不把完整 task 文件内容拼进 prompt

分三类线程：

1. `family planner thread`
   - 读取完整 `source_task/`
   - 产出 4 个派生任务 blueprint

2. `task writer thread`
   - 每个 blueprint 单独一个新 thread
   - 自由读取 `source_task/`
   - 生成当前任务前，先检查同一 workspace 的 `drafts/` 中已完成的 sibling tasks
   - 把完整任务写到 `drafts/<derived_task_id>/`

3. `reviewer thread`
   - 联合读取 `drafts/` 下 4 个任务
   - 输出任务级 verdict 与 family 级观察

### 4. Prompt 设计

`src/prompts.ts` 只存控制性 prompt，不搬运上下文。

#### family planner prompt

要求 Codex：

- 阅读 `source_task/` 整个目录
- 基于 source task 与其 shipped skills，设计 4 个全新派生任务
- 继承领域和技能收益
- 不得复写原任务目标
- 4 个任务中固定包含 1 个 `similar` 任务和 3 个 `transfer` 任务
- `similar` 任务允许与原任务较接近，用于测试技能有效性
- 3 个 `transfer` 任务必须彼此明显不同，用于测试技能泛化性
- 任务命名必须让人一眼看出哪个是 `similar`，哪个是 `transfer`
- `instruction.md` 应尽量避免直接明示要使用技能，也不能引入 source task 没写过的具体 skill 名称
- 如果 source task 本身已经显式写出技术或技能名称，派生任务沿用同等级别表述可以接受，但不能写得比 source task 更直接

#### task writer prompt

要求 Codex：

- 基于单个 blueprint 生成完整任务包
- 写入 `drafts/<derived_task_id>/`
- 生成当前任务前，先检查当前 workspace 的 `drafts/`
- 把当前 `drafts/<derived_task_id>/` 视为当前目录，不当作已有 sibling task
- 对已有 sibling tasks 优先读取 `PLAN.json`、`instruction.md`、`task.toml`
- 如有必要，再读取 `tests/test_outputs.py` 和 `environment/` 下输入资产
- 尽量避免与已有 sibling tasks 在任务场景、输入资产、输出目标和测试判定方式上过于接近
- 只允许调整当前任务的具体情境、输入资产、验证方式和 instruction 文案，不能改 blueprint 中已经固定的 `derivedTaskId`、`taskRole`、`primaryOutputFile`、`source_task_id` 和 skill scope
- 固定生成：
  - `task.toml`
  - `instruction.md`
  - `environment/`
  - `solution/`
  - `tests/`
- `instruction.md` 只能描述任务目标、输入、输出、规则、成功条件
- 不允许直接告诉 agent “去使用某个技能”

#### reviewer prompt

要求 Codex：

- 对每个任务分别检查：
  - 以 source task 的 `instruction.md` 为基线，检查派生任务是否写得更直接，或是否引入了 source task 未出现的具体 skill 名称
  - 测试是否可判定
  - 任务是否真的能从 shipped skills 受益
  - 该任务是否应通过 reviewer
- 对 family 整体额外给出观察：
  - family 是否满足“1 个 `similar` + 3 个 `transfer`”
  - 3 个 `transfer` 任务是否彼此足够不同
  - `similar` 任务是否足够接近原任务，能够用于测试技能有效性
- 任务级 verdict 只阻塞对应任务，不阻塞整组

### 5. 结构化输出范围

`src/schema.ts` 只约束“规划输出”和“审查输出”。

不要求 Codex 把整个任务目录包装成一个超大 JSON。

#### `FamilyPlanSchema`

每个 source task 输出一个 family plan，包含：

- `sourceTaskId`
- `familyTheme`
- `derivedTasks`

`derivedTasks` 固定恰好 4 个元素，每个元素包含：

- `derivedTaskId`
- `taskRole`
- `title`
- `goal`
- `primaryOutputFile`
- `difficulty`
- `category`
- `skillBenefitRationale`

#### `ReviewResultSchema`

包含：

- `taskResults[]`
  - `derivedTaskId`
  - `pass`
  - `issues[]`
  - `visibilityPass`
  - `skillBenefitPass`
  - `testabilityPass`
- `familyObservations`
  - `issues[]`
  - `diversityPass`
  - `roleLayoutPass`

完整任务文件由 Codex 直接写入 `drafts/`，不走 JSON 承载。

### 6. 任务落盘

`src/materialize.ts` 从 `drafts/<derived_task_id>/` 读取结果，并执行本地检查。

发布目标：

```text
/home/levi/Harbor/tasks_library/integrated_tasks/<source_task_id>/<derived_task_id>/
```

规则：

- 允许向已存在的 `integrated_tasks/<source_task_id>/` 追加任务
- 同名 `derivedTaskId` 目录已存在时，跳过该任务
- 不覆盖
- 不删除
- 不修改已有任务目录

每个任务必须至少包含：

- `task.toml`
- `instruction.md`
- `environment/Dockerfile`
- `environment/skills/**`
- `solution/solve.sh`
- `tests/test.sh`
- `tests/test_outputs.py`

### 7. 校验阶段

`src/validate.ts` 负责三层校验，但发布决策改为任务级。

#### 静态校验

- 必备文件存在
- `task.toml` 中的 `id` 与目录名一致
- `environment/Dockerfile` 必须把 `skills` 复制到 `/root/.codex/skills`

#### 运行校验

对每个任务执行：

1. 调用 Harbor CLI 的官方 oracle：`harbor run -p <task_dir> -a oracle --force-build --jobs-dir <logs_dir> --job-name <job_name>`
2. 解析 trial 的 `result.json`（`exception_info` / `verifier_result.rewards`）
3. 约定 `reward >= 1.0` 视为通过，否则该任务不发布

任一步失败则该任务不发布。

补充：

- runtime 失败在 metadata 中区分为 `harbor-preflight` / `harbor-run` / `harbor-reward`

#### family 校验

同一个 source family 下的 4 个任务必须满足：

- `derivedTaskId` 不同
- `primaryOutputFile` 不同

说明：

- `1 similar + 3 transfer`
- `derivedTaskId` 中是否包含 `-similar-` / `-transfer-`
- `per-skill` 模式下，如果 planner 漏掉目标 skill slug，程序会在落盘前自动补齐后再做 family 校验

不再作为整组发布硬门槛，而是 planner 默认目标与 reviewer/family observation。


### 8. manifest 记录

`src/manifest.ts` 维护运行日志，例如：

```json
{
  "runId": "20260311-3d-scan-calc-001",
  "sourceTaskId": "3d-scan-calc",
  "derivedTaskId": "3d-scan-calc-component-audit-v2",
  "phase": "validate",
  "threadId": "xxx",
  "status": "passed",
  "draftDir": "/tmp/...",
  "publishedDir": "/home/levi/Harbor/tasks_library/integrated_tasks/...",
  "issues": []
}
```

字段至少包含：

- `runId`
- `sourceTaskId`
- `derivedTaskId`
- `phase`
- `threadId`
- `status`
- `draftDir`
- `publishedDir`
- `issues`

补充约定：

- source-level `reviewer` / `validate` 记录表示阶段执行完成
- 若仅部分任务失败，失败信息写入 `issues`，任务分流写入 `metadata`
- 最终是否发布，以 `publish` phase 和 run summary 为准

### 9. CLI 设计

`src/cli.ts` 提供以下命令：

#### `inventory`

扫描：

```text
/home/levi/Harbor/tasks_library/skillsbench/tasks
```

输出 source task 清单及其 skill 概况。

#### `generate-family --source-task-id <id>`

对单个 source task 生成完整 4-task family。

#### `batch --match <regex> --limit <n> --family-concurrency <n>`

批量跑多个 source task。

#### `review --source-task-id <id>`

对某个 family 的 `drafts/` 或已生成目录单独做 reviewer pass。

默认参数固定：

- `tasksPerFamily = 4`
- `familyConcurrency = 2`
- `plannerRetries = 1`
- `writerRetries = 1`
- `reviewRetries = 1`
- 已存在 family 目录时允许追加新任务
- 已存在同名任务目录时跳过该任务

## Generation Flow

对每个 source task 固定执行以下流程：

1. 创建 scratch workspace
2. 复制完整 source task 到 `source_task/`
3. 启动 `family planner thread`
4. 生成 4 个 blueprint
5. 对 4 个 blueprint 分别启动 `task writer thread`
6. writer 按顺序检查当前 `drafts/` 中已经生成好的 sibling tasks，并把完整任务写入 `drafts/<derived_task_id>/`
7. 启动 `reviewer thread`
8. reviewer 返回任务级 verdict 与 family 级观察
9. 对每个任务执行本地静态校验
10. `batch` 模式在启动生成前先做一次运行时 preflight（`harbor` + `docker`）
11. 对通过前置检查的任务执行 Harbor Oracle(runtime) 校验（`harbor run -p <task_dir> -a oracle --force-build --jobs-dir <logs_dir> --job-name <job_name>`）
12. 按任务把通过验收的结果复制到 `integrated_tasks/`

## Generation Rules

### 1. 派生任务规则

每个 source task 固定生成 4 个全新派生任务，且：

- 保留 source task 所在领域
- 保留 source task 中 shipped skills 的收益点
- family 固定由 1 个 `similar` 任务和 3 个 `transfer` 任务组成
- `similar` 任务允许与原任务接近，但不能只是“原任务轻微改名”
- 3 个 `transfer` 任务必须彼此明显不同
- `transfer` 任务应保留 skill 的核心收益点，但在目标、输入组织、输出契约或应用场景上发生迁移
- `similar` 任务用于测试技能有效性，`transfer` 任务用于测试技能泛化性

说明：

- 上面仍是默认生成目标
- 后续发布按单任务验收结果决定，不再要求整组都通过才发布

### 2. instruction 规则

`instruction.md` 必须：

- 只写问题描述
- 只写输入文件
- 只写输出要求
- 只写规则与成功标准

`instruction.md` 禁止：

- 直接说要用某个 skill
- 直接说环境里预装了某能力
- 直接给出 skill 路径
- 直接出现具体 skill 名称

### 3. 技能收益规则

技能收益不体现在 `instruction.md` 的明文提示上，而体现在：

- 任务设计本身依赖复杂能力
- shipped skills 恰好覆盖关键难点
- 不用 skill 仍然可以做，但更难、更慢或更容易出错

这部分只出现在：

- blueprint 的隐藏字段 `skillBenefitRationale`
- reviewer 的内部审查结果

### 4. 资产复制规则

对每个派生任务：

- 保留 `environment/skills/**`
- 复制该派生任务真正需要的 source task 输入资产
- 不复制明显无关的大型资产
- `environment/Dockerfile` 必须把 `skills` 复制到 `/root/.codex/skills`

### 5. 命名规则

- family 目录名固定为 `source_task_id`
- `derivedTaskId` 使用 kebab-case
- `derivedTaskId` 必须显式包含任务角色：
  - `similar` 任务包含 `-similar-`
  - `transfer` 任务包含 `-transfer-`
- `per-skill` 模式下，`derivedTaskId` 还应包含目标 skill slug；如果 planner 漏写，CLI 会在落盘前自动补齐
- `task.toml` 中 `metadata.id` 必须等于目录名
- `metadata.name` 必须显式标明任务角色，让人一眼看出是 `Similar` 还是 `Transfer`
- 4 个任务的主输出文件名必须不同

## Test Plan

### 1. 工程级测试

- `inventory` 能扫描全部 source task
- 每个 source task 都能识别到 `environment/skills`
- `family planner` 每次都返回恰好 4 个 blueprint
- 4 个 `derivedTaskId` 唯一
- `test:prompts` 能断言 writer prompt 明确要求读取当前 workspace 的已有 `drafts/`

### 2. reviewer 语义审查测试

对每个生成 family，reviewer 必须给出：

- 每个任务自己的：
  - `visibilityPass`
  - `skillBenefitPass`
  - `testabilityPass`
  - `pass/fail`
- family 自己的：
  - `diversityPass`
  - `roleLayoutPass`

规则：

- 任务级 `pass=false` 只阻塞对应任务
- family 级 observation 不阻塞其他任务发布

### 3. family 结构测试

同一个 family 下：

- 4 个 `derivedTaskId` 不同
- 4 个 `primaryOutputFile` 不同

其中：

- 恰好 1 个 `derivedTaskId` 包含 `-similar-`
- 恰好 3 个 `derivedTaskId` 包含 `-transfer-`
- `per-skill` family 中每个 `derivedTaskId` 还应包含目标 skill slug

改为 reviewer / observation 层面的检查，不再作为整组发布硬门槛。

### 4. 运行测试

先跑三个代表性 family：

- `3d-scan-calc`
- `adaptive-cruise-control`
- `azure-bgp-oscillation-route-leak`

每个 family 都必须通过：

- planner
- writer
- reviewer
- 对于准备发布的单个任务：
  - static validate
  - Harbor Oracle(runtime) 校验（`harbor run -p <task_dir> -a oracle --force-build --jobs-dir <logs_dir> --job-name <job_name>`，约定 `reward >= 1.0` 通过）

### 5. 批量测试

- `batch --limit 3` 能连续生成 3 个 family
- manifest 能记录成功、失败、跳过
- 已存在 family 再跑时允许追加新任务
- 已存在同名任务目录时跳过，不覆盖

## Assumptions

- 实现完全独立于 `harbor_skill_pipeline`，包括不参考其 prompt、schema、目录逻辑、校验逻辑和测试代码。
- 使用 Codex SDK 的 `workingDirectory` 模式，让 Codex 在本地完整工作区内自由读文件，而不是把整个 task 打包进 prompt。
- `instruction.md` 应尽量避免直接明示技能；是否越界要以 source task 的原始表述为基线做 reviewer 语义审查，`environment/skills/**` 保留原样。
- 完整任务文件由 Codex 直接写到 `drafts/`，结构化 schema 只用于 blueprint 和 reviewer。
- 不做任何删除操作；已有目标目录只跳过。

## 如果你用 codex sdk 需要 `OPENAI_API_KEY`，请使用你自己的实际密钥，例如 `OPENAI_API_KEY="your_api_key_here"`
