# `codex_task_builder` 使用说明

## 1. 作用

`codex_task_builder/` 是一个独立的 Node/TypeScript 工具，用来基于 `Codex SDK` 从现有 source task 批量生成 Harbor 风格的 `integrated_tasks`。

当前固定约束：

- 输入目录：`/home/levi/Harbor/tasks_library/skillsbench/tasks`
- 输出目录：`/home/levi/Harbor/tasks_library/integrated_tasks`
- 每个 source task 生成一个 4-task family
- family 固定为：
  - `1` 个 `similar`
  - `3` 个 `transfer`
- 不覆盖已有 family
- 不做删除操作

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
- 如果要跑运行校验，需要本机有 `docker`

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
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks
```

作用：

- 为一个 source task 创建 scratch workspace
- 调用 Codex SDK 做 planner、writer、reviewer
- 做静态校验与运行校验
- 校验通过后发布到 `integrated_tasks/<source_task_id>/`

行为说明：

- 如果目标 family 已存在，会直接跳过
- 不会覆盖已有结果
- 不会删除任何目录

### 4.3 批量生成

```bash
cd /home/levi/Harbor/codex_task_builder
npm run batch -- \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks \
  --limit 3 \
  --family-concurrency 2
```

可选参数：

- `--match <regex>`：按 `sourceTaskId` 过滤
- `--limit <n>`：限制 family 数量
- `--family-concurrency <n>`：并发生成 family 数量

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
/tmp/harbor-codex-task-builder/<run_id>/<source_task_id>/
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

### 5.3 最终发布目录

发布成功后，任务会进入：

```text
/home/levi/Harbor/tasks_library/integrated_tasks/<source_task_id>/<derived_task_id>/
```

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
5. reviewer 做 family 级语义审查
6. 本地做静态校验
7. 本地做 Docker build + solution/test 运行校验
8. 校验通过后发布到 `integrated_tasks/`

## 8. 当前硬规则

目前本地程序会硬检查：

- `derivedTaskId` 唯一
- `primaryOutputFile` 唯一
- family 角色布局是 `1 similar + 3 transfer`
- `similar` 的 id 含 `-similar-`
- `transfer` 的 id 含 `-transfer-`
- 必备文件存在
- `task.toml` 中 `id` 与目录名一致
- `environment/Dockerfile` 保留 `COPY skills /root/.codex/skills`

## 9. 结果判断

如果单个 family 成功发布，CLI 最终会返回类似：

```json
{
  "sourceTaskId": "citation-check",
  "runId": "20260311140649-citation-check-x2n6e3",
  "status": "completed",
  "issues": [],
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
    "runtime:xxx docker build 失败"
  ]
}
```

如果目标已存在，则会返回：

```json
{
  "sourceTaskId": "3d-scan-calc",
  "status": "skipped",
  "issues": [
    "目标 family 目录已存在，按配置跳过"
  ]
}
```

## 10. 当前限制

- `review` 命令依赖最近一次 workspace 中已有 `family-plan.json`
- 真实生成耗时可能较长，尤其是 skill 很大、source task 很复杂时
- 运行校验依赖 `docker`
- 当前 family 生成是顺序 writer，不是 4 个 writer 并发
