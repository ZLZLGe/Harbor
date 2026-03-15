# `codex_task_builder` 使用说明

## 1. 作用

`codex_task_builder/` 是一个独立的 Node/TypeScript 工具，用来基于 `Codex SDK` 从现有 source task 批量生成 Harbor 风格的 `integrated_tasks`。

当前固定约束：

- 输入目录：`/home/levi/Harbor/tasks_library/skillsbench/tasks`
- 输出目录：`/home/levi/Harbor/tasks_library/integrated_tasks`
- 每个 source task 默认尝试生成一个 4-task family
- 默认目标为：
  - `1` 个 `similar`
  - `3` 个 `transfer`
- 按任务验收、按任务发布
- reviewer / 静态检查 / Oracle(runtime) 只阻塞对应任务
- 允许向已有 `integrated_tasks/<source_task_id>/` 追加新任务
- 不覆盖已有同名任务目录
- 不做删除操作

技能作用域模式：

- `all`
  - 默认模式
  - 一个 source task 的全部 skills 共同参与一个 family 的设计
- `per-skill`
  - 严格单技能模式
  - 一个多-skill source task 会拆成多个 family
  - 每个 family 只保留一个 shipped skill
  - 其他 source task skills 不会作为背景或隐含依赖出现

## 2. 目录结构

```text
codex_task_builder/
  package.json
  tsconfig.json
  src/
    cli.ts
    codex.ts
    discovery.ts
    manifest.ts
    materialize.ts
    prompts.ts
    schema.ts
    utils.ts
    validate.ts
    workspace.ts
```

## 3. 依赖与前提

需要：

- Node.js 18+
- 本机可用的 `codex` CLI
- 有效的模型认证环境，例如 `OPENAI_API_KEY`
- 如果要跑运行校验，需要本机有 `harbor` CLI 与 `docker`

安装依赖：

```bash
cd /home/levi/Harbor/codex_task_builder
npm install
```

类型检查：

```bash
npm run check
```

## 4. 常用命令

### 4.1 扫描 source tasks

```bash
cd /home/levi/Harbor/codex_task_builder
npm run inventory -- --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks
```

作用：

- 扫描全部 source task
- 输出每个任务的基础元信息
- 输出该任务包含的 skill 名称
- 输出 `environment/` 下的非 skill 资产

### 4.2 生成单个 family

```bash
cd /home/levi/Harbor/codex_task_builder
npm run generate-family -- \
  --source-task-id citation-check \
  --skill-mode all \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks
```

作用：

- 为一个 source task 创建 scratch workspace
- 调用 Codex SDK 做 planner、writer、reviewer
- 对每个任务分别做 reviewer、静态校验与运行校验
- 通过验收的任务发布到 `integrated_tasks/<source_task_id>/`

行为说明：

- 已有 family 目录时不会整组跳过
- 会把本次新通过的任务追加进去
- 已有同名任务目录会跳过
- 不会覆盖已有结果
- 不会删除任何目录

严格单技能模式示例：

```bash
cd /home/levi/Harbor/codex_task_builder
npm run generate-family -- \
  --source-task-id citation-check \
  --skill-mode per-skill \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks
```

补充说明：

- `--skill-mode all`：保留原始 source task 的全部 shipped skills
- `--skill-mode per-skill`：对 source task 中的每个 skill 分别生成一个 family
- `per-skill` 模式下，workspace 和 drafts 中只会保留当前目标 skill，其余 skills 不会被复制进去
- 如果 planner 漏掉目标 skill slug，程序会在落盘前自动把该 slug 补进 `derivedTaskId`，然后再继续做静态校验和运行校验

### 4.3 批量生成

```bash
cd /home/levi/Harbor/codex_task_builder
export CODEX_TASK_BUILDER_MODEL=gpt-5.4
npm run batch -- \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks \
  --skill-mode per-skill \
  --limit 10 \
  --family-concurrency 4
```

可选参数：

- `--match <regex>`：按 `sourceTaskId` 过滤
- `--limit <n>`：限制 family 数量
- `--family-concurrency <n>`：并发生成 family 数量
- `--skill-mode <all|per-skill>`：选择使用全部 skills 还是严格单技能拆分模式

当前行为补充：

- `batch` 在真正生成前会先做一次运行时 preflight（`harbor` + `docker`）
- 如果 preflight 失败，本轮 batch 会直接返回失败结果，不会启动 planner / writer / reviewer
- 运行时环境异常会在 `issues` 和 `metadata.runtimePreflight` 中单独标明

示例：

```bash
npm run batch -- \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks \
  --match 'citation|travel' \
  --limit 2 \
  --family-concurrency 1
```

### 4.4 对最近一次 scratch run 重新做 reviewer

```bash
cd /home/levi/Harbor/codex_task_builder
npm run review -- \
  --source-task-id citation-check \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks
```

作用：

- 找到该 source task 最近一次 scratch workspace
- 读取 `family-plan.json`
- 重新跑 reviewer

注意：

- 如果该 workspace 还没有生成 `family-plan.json`，说明 planner 还没落盘完成或生成未到该阶段，此命令会报错

## 5. 运行时目录

### 5.1 scratch workspace

每次运行会创建：

```text
/home/levi/Harbor/codex_task_builder_runs/scratch/<run_id>/<source_task_id>/
```

里面通常包含：

```text
source_task/
drafts/
artifacts/
TASK_BUILDER_BRIEF.md
```

说明：

- `source_task/`：完整复制的原始 source task
- `drafts/`：Codex 写出的派生任务草稿
- `artifacts/`：中间产物，例如 family plan、writer summary、review result、运行日志

### 5.2 manifest

运行记录写到：

```text
/home/levi/Harbor/codex_task_builder_runs/manifest.jsonl
```

每条记录会标出：

- `runId`
- `sourceTaskId`
- `phase`
- `status`
- `threadId`
- `draftDir`
- `publishedDir`
- `issues`

补充说明：

- source-level 的 `reviewer` / `validate` 记录表示该阶段已经执行完成
- 如果只有部分任务不通过，问题会写进 `issues`，任务拆分会写进 `metadata`
- 是否最终发布，以 `publish` phase 和最终 run summary 为准
- `batch` 预检失败时，会额外写入 `runtime-preflight` phase

### 5.3 最终发布目录

发布成功后，任务会进入：

```text
/home/levi/Harbor/tasks_library/integrated_tasks/<source_task_id>/<derived_task_id>/
```

补充说明：

- 如果手动用 Harbor 跑整组任务，`harbor run -p` 应指向 `/home/levi/Harbor/tasks_library/integrated_tasks/<source_task_id>/`
- 如果只跑单个任务，`harbor run -p` 也可以直接指向更深一层的 `<derived_task_id>/`
- 不应直接把 `-p` 指向 `/home/levi/Harbor/tasks_library/integrated_tasks/` 根目录

## 6. 环境变量

当前实现会读取以下环境变量：

- `OPENAI_API_KEY`
  - 提供给 `codex` CLI 的模型认证
- `CODEX_PATH`
  - 可选，覆盖默认 `codex` 可执行文件路径
- `CODEX_TASK_BUILDER_MODEL`
  - 可选，指定生成时使用的模型
- `CODEX_TASK_BUILDER_NETWORK_ACCESS`
  - 可选，值为 `1` 时开启网络访问

示例：

```bash
export OPENAI_API_KEY="your_api_key_here"
export CODEX_TASK_BUILDER_MODEL=gpt-5.2
export CODEX_TASK_BUILDER_NETWORK_ACCESS=1
```

## 7. 当前生成流程

对单个 source task，工具会按下面的顺序执行：

1. 创建 scratch workspace
2. 复制完整 `source_task/`
3. planner 生成 family 规划
4. 为 4 个派生任务分别运行 writer
5. reviewer 返回任务级 verdict 和 family 级观察
6. 对每个任务做本地静态校验
7. 对通过前置检查的任务做 Harbor Oracle(runtime) 运行校验（`harbor run -p <task_dir> -a oracle --force-build --jobs-dir <logs_dir> --job-name <job_name>`）
8. 按任务把通过验收的结果发布到 `integrated_tasks/`

运行校验补充：

- 运行校验对齐 Harbor 官方 oracle：调用 `harbor run -p <task_dir> -a oracle --force-build --jobs-dir <logs_dir> --job-name <job_name>`
- 结果以 `trial result.json` 中的 `verifier_result.rewards` 为准（约定 `reward >= 1.0` 视为通过）
- runtime 失败会在 metadata 区分为 `harbor-preflight` / `harbor-run` / `harbor-reward`

## 8. 当前硬规则

目前本地程序会硬检查：

- `derivedTaskId` 唯一
- `primaryOutputFile` 唯一
- 必备文件存在
- `task.toml` 中 `id` 与目录名一致
- `metadata.name` 仍需显式包含 `Similar` 或 `Transfer`
- `environment/Dockerfile` 保留 `COPY skills /root/.codex/skills`

说明：

- `1 similar + 3 transfer`
- `derivedTaskId` 是否包含 `-similar-` / `-transfer-`

现在属于 planner 默认目标与 reviewer/family observation，不再作为整组发布硬门槛。

## 9. 结果判断

如果单个 family 成功发布，CLI 最终会返回类似：

```json
{
  "sourceTaskId": "citation-check",
  "runId": "20260311140649-citation-check-x2n6e3",
  "status": "completed",
  "issues": [
    "reviewer:preprint-transfer-publication-reconciliation skillBenefitPass=false"
  ],
  "familyObservationIssues": [],
  "publishedTaskIds": [
    "grant-proposal-similar-citation-integrity-audit",
    "related-work-transfer-search-driven-bibliography",
    "bibliography-transfer-validation-triage"
  ],
  "skippedTaskIds": [],
  "failedTaskIds": [
    "preprint-transfer-publication-reconciliation"
  ],
  "publishedDir": "/home/levi/Harbor/tasks_library/integrated_tasks/citation-check"
}
```

如果失败，通常会返回：

```json
{
  "sourceTaskId": "citation-check",
  "runId": "20260311140649-citation-check-x2n6e3",
  "status": "failed",
  "issues": [
    "runtime:xxx harbor verifier reward=0.0 < 1.0"
  ],
  "familyObservationIssues": [],
  "publishedTaskIds": [],
  "skippedTaskIds": [],
  "failedTaskIds": [
    "xxx"
  ]
}
```

如果本次没有新任务发布，但通过的任务都已经存在，则会返回：

```json
{
  "sourceTaskId": "3d-scan-calc",
  "runId": "20260311140649-3d-scan-calc-abc123",
  "status": "skipped",
  "issues": [],
  "familyObservationIssues": [],
  "publishedTaskIds": [],
  "skippedTaskIds": [
    "3d-scan-calc-similar-foo"
  ],
  "failedTaskIds": [],
  "publishedDir": "/home/levi/Harbor/tasks_library/integrated_tasks/3d-scan-calc"
}
```

## 10. 当前验证样例

当前仓库里，`pdf-excel-diff` 已经验证过：

- `--skill-mode all` 可以生成并发布可运行的 family
- `--skill-mode per-skill` 可以按单技能拆分并发布可运行的 family
- 对最终发布目录手动运行 Harbor 时，应把 `-p` 指向某个 family 目录，例如 `/home/levi/Harbor/tasks_library/integrated_tasks/pdf-excel-diff/`

## 11. 当前限制

- `review` 命令依赖最近一次 workspace 中已有 `family-plan.json`
- 真实生成耗时可能较长，尤其是 skill 很大、source task 很复杂时
- 运行校验依赖 `harbor` 与 `docker`
- 当前 family 生成是顺序 writer，不是 4 个 writer 并发
