# codex_task_builder

`codex_task_builder/` 是一个独立的 Node.js + TypeScript 工具，用来基于 Codex SDK 从现有 source task 生成 Harbor 风格的 `integrated_tasks`。

## 当前能力

- 扫描 source task 元信息与 skill
- 支持 `all` / `per-skill` 两种技能作用域模式
- 为单个 source task 或单个目标 skill 规划并生成 family
- 批量生成多个 family
- 对最近一次 scratch run 重新执行 reviewer

当前仓库里，`pdf-excel-diff` 这个 source task 已经验证过：

- `--skill-mode all` 可以生成并发布可运行的 family
- `--skill-mode per-skill` 可以按单技能拆分并发布可运行的 family
- 手动做 Harbor 校验时，应把 `harbor run -p` 指向某个 family 目录或单任务目录，不能直接指向 `integrated_tasks/` 根目录

当前实现里的默认目录是固定的：

- source root: `/home/levi/Harbor/tasks_library/skillsbench/tasks`
- output root: `/home/levi/Harbor/tasks_library/integrated_tasks`
- runs root: `/home/levi/Harbor/codex_task_builder_runs`
- scratch root: `/home/levi/Harbor/codex_task_builder_runs/scratch`

## 前提

需要：

- Node.js 18+
- `npm`
- 本机可用的 `codex` CLI
- 有效的模型认证环境变量，例如 `OPENAI_API_KEY`
- 如果要做运行校验，默认需要本机有 `harbor` CLI，并且当前 shell 已导出 `DAYTONA_API_KEY`
- 如果想切回旧的 docker 路线，需要额外导出 `CODEX_TASK_BUILDER_RUNTIME_ENV=docker`，并保证本机有 `docker`

安装依赖：

```bash
cd /home/levi/Harbor/codex_task_builder
npm install
```

类型检查：

```bash
npm run check
```

最小 prompt 单测：

```bash
npm run test:prompts
```

## 快速开始

扫描 source task：

```bash
cd /home/levi/Harbor/codex_task_builder
npm run inventory -- --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks
```

生成单个 family：

```bash
cd /home/levi/Harbor/codex_task_builder
export DAYTONA_API_KEY="your_daytona_api_key_here"
npm run generate-family -- \
  --source-task-id citation-check \
  --skill-mode all \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks
```

严格单技能模式：

```bash
cd /home/levi/Harbor/codex_task_builder
npm run generate-family -- \
  --source-task-id citation-check \
  --skill-mode per-skill \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks
```

说明：

- `--skill-mode all`：保持现状，一个 source task 的全部 skills 共同参与一个 family 的设计
- `--skill-mode per-skill`：把一个 source task 按 skill 拆成多个 family，每个 family 只保留一个 shipped skill
- `per-skill` 是严格单技能模式：其他 source task skills 不会出现在 workspace、drafts 或 prompt 中，也不允许作为背景依赖
- `per-skill` 模式下，如果 planner 漏掉目标 skill slug，程序会在落盘前自动把该 slug 补进 `derivedTaskId`，随后继续做静态校验和运行校验

批量生成：

```bash
cd /home/levi/Harbor/codex_task_builder
export DAYTONA_API_KEY="your_daytona_api_key_here"
npm run batch -- \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks \
  --skill-mode per-skill \
  --limit 3 \
  --family-concurrency 2
```

说明：

- `generate-family` 和 `batch` 在真正启动 planner 之前，都会先做一次运行时 preflight
- 默认 preflight 检查 `harbor` CLI 与 `DAYTONA_API_KEY`
- 当 `CODEX_TASK_BUILDER_RUNTIME_ENV=docker` 时，preflight 会改为检查 `harbor` CLI 与 `docker`
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
- `DAYTONA_API_KEY`
  - 默认 runtime 校验后端 Daytona 的认证环境变量
- `CODEX_PATH`
  - 可选，覆盖默认 `codex` 可执行文件路径
- `CODEX_TASK_BUILDER_MODEL`
  - 可选，指定模型
- `CODEX_TASK_BUILDER_NETWORK_ACCESS`
  - 可选，值为 `1` 时开启网络访问
- `CODEX_TASK_BUILDER_RUNTIME_ENV`
  - 可选，默认值为 `daytona`
  - 当前只支持 `daytona` 和 `docker`
  - 设为 `docker` 时，会切回旧的 docker runtime 校验路径

示例：

```bash
export OPENAI_API_KEY="your_api_key_here"
export DAYTONA_API_KEY="your_daytona_api_key_here"
export CODEX_TASK_BUILDER_MODEL="gpt-5.2"
export CODEX_TASK_BUILDER_NETWORK_ACCESS=1
```

## 说明

- 每次运行会创建 scratch workspace：`/home/levi/Harbor/codex_task_builder_runs/scratch/<run_id>/<source_task_id>/`
- manifest 会写到：`/home/levi/Harbor/codex_task_builder_runs/manifest.jsonl`
- 发布成功后会写入：`/home/levi/Harbor/tasks_library/integrated_tasks/<source_task_id>/`
- `per-skill` 模式下，一个多-skill source task 会展开成多个独立 family
- 当前实现按任务验收、按任务发布
- 已有 `integrated_tasks/<source_task_id>/` 时允许追加新任务
- 已有同名 `derived_task_id/` 目录时会跳过该任务，不会覆盖
- 同一 scratch workspace 内，后续 writer 会先直接检查 `drafts/` 下已经生成好的 sibling tasks，并尽量避免与它们在场景、输入资产、输出目标和测试方式上重复；这属于 prompt 级软约束，不是硬校验
- `task.toml` 的关键 metadata（如 `description`、`primary_output_file`、`source_task_id`、`task_role`）现在属于 static validate 硬门槛；缺失或不匹配会直接阻止发布
- runtime 校验对齐 Harbor 官方 oracle：默认调用 `harbor run -p <task_dir> -a oracle -e daytona --force-build --jobs-dir <logs_dir> --job-name <job_name>`
- 如果设置 `CODEX_TASK_BUILDER_RUNTIME_ENV=docker`，则会改为 `-e docker`
- 如果手动调用 Harbor，`harbor run -p` 应指向 `integrated_tasks/<source_task_id>/` 这一级 family 目录，或更深一层的单任务目录；不能直接指向 `integrated_tasks/` 根目录
- 运行时宿主异常仍会记作 runtime 失败，但会在日志和 metadata 里单独标明
- 当前实现不会做删除操作

## 当前验证情况

- `npm run check` 可通过
- `npm run inventory -- --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks` 可执行
- `pdf-excel-diff` 已经在 `all` / `per-skill` 两种技能作用域下生成并发布成功
- 对最终发布目录做 Harbor oracle 校验时，应按 family 目录逐个执行；例如 `/home/levi/Harbor/tasks_library/integrated_tasks/pdf-excel-diff/`

更详细的中文设计和使用说明可以看：

- `/home/levi/Harbor/docs/codex_task_builder_usage_zh.md`
- `/home/levi/Harbor/docs/codex_sdk_full_task_builder_plan.md`

/home/levi/Harbor/codex_task_builder/tmp/review_errors_codex_repair_20260325.ts 用这个进行重新review 修复