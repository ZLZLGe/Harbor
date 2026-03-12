# codex_task_builder

`codex_task_builder/` 是一个独立的 Node.js + TypeScript 工具，用来基于 Codex SDK 从现有 source task 生成 Harbor 风格的 `integrated_tasks`。

## 当前能力

- 扫描 source task 元信息与 skill
- 为单个 source task 规划并生成一个 family
- 批量生成多个 family
- 对最近一次 scratch run 重新执行 reviewer

当前实现里的默认目录是固定的：

- source root: `/home/levi/Harbor/tasks_library/skillsbench/tasks`
- output root: `/home/levi/Harbor/tasks_library/integrated_tasks`
- runs root: `/home/levi/Harbor/codex_task_builder_runs`
- scratch root: `/tmp/harbor-codex-task-builder`

## 前提

需要：

- Node.js 18+
- `npm`
- 本机可用的 `codex` CLI
- 有效的模型认证环境变量，例如 `OPENAI_API_KEY`
- 如果要做运行校验，需要本机有 `docker`

安装依赖：

```bash
cd /home/levi/Harbor/codex_task_builder
npm install
```

类型检查：

```bash
npm run check
```

我本地已经确认 `npm run check` 可以通过。

## 快速开始

扫描 source task：

```bash
cd /home/levi/Harbor/codex_task_builder
npm run inventory -- --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks
```

我本地已经确认这条命令可以执行并输出任务清单。

生成单个 family：

```bash
cd /home/levi/Harbor/codex_task_builder
npm run generate-family -- \
  --source-task-id citation-check \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks
```

批量生成：

```bash
cd /home/levi/Harbor/codex_task_builder
npm run batch -- \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks \
  --limit 3 \
  --family-concurrency 2
```

说明：

- `batch` 在真正启动 planner 之前，会先做一次 Docker/WSL preflight
- 如果 preflight 失败，本轮 batch 会直接返回失败结果，不会启动生成

重新执行最近一次 reviewer：

```bash
cd /home/levi/Harbor/codex_task_builder
npm run review -- \
  --source-task-id citation-check \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks
```

## 环境变量

- `OPENAI_API_KEY`
  - 提供给 `codex` CLI 的模型认证
- `CODEX_PATH`
  - 可选，覆盖默认 `codex` 可执行文件路径
- `CODEX_TASK_BUILDER_MODEL`
  - 可选，指定模型
- `CODEX_TASK_BUILDER_NETWORK_ACCESS`
  - 可选，值为 `1` 时开启网络访问

示例：

```bash
export OPENAI_API_KEY="your_api_key_here"
export CODEX_TASK_BUILDER_MODEL="gpt-5.2"
export CODEX_TASK_BUILDER_NETWORK_ACCESS=1
```

## 说明

- 每次运行会创建 scratch workspace：`/tmp/harbor-codex-task-builder/<run_id>/<source_task_id>/`
- manifest 会写到：`/home/levi/Harbor/codex_task_builder_runs/manifest.jsonl`
- 发布成功后会写入：`/home/levi/Harbor/tasks_library/integrated_tasks/<source_task_id>/`
- 当前实现按任务验收、按任务发布
- 已有 `integrated_tasks/<source_task_id>/` 时允许追加新任务
- 已有同名 `derived_task_id/` 目录时会跳过该任务，不会覆盖
- runtime 校验会用 `bash /solution/solve.sh && bash /tests/test.sh` 执行脚本
- Docker/WSL 宿主异常仍会记作 runtime 失败，但会在日志和 metadata 里单独标明
- 当前实现不会做删除操作

## 我目前确认到的范围

- 我已经本地验证 `npm run check` 可通过
- 我已经本地验证 `npm run inventory -- --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks` 可执行
- 我还没有完整验证 `generate-family` / `batch` / `review` 的端到端流程，因为这些步骤依赖本机 `codex` 认证、模型可用性，以及部分场景下的 `docker`

更详细的中文设计和使用说明可以看：

- `/home/levi/Harbor/docs/codex_task_builder_usage_zh.md`
- `/home/levi/Harbor/docs/codex_sdk_full_task_builder_plan.md`
