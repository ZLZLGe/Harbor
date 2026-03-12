# Harbor

本仓库用于 **skill → task** 的数据管线：基于带有 shipped skills 的 *source tasks*，自动合成符合 **Harbor task spec** 的派生任务（`integrated_tasks`），用于后续 *skill editing* 研究。

- Harbor task spec：<https://harborframework.com/docs>
- source tasks：`tasks_library/skillsbench/tasks/`
- generated tasks：`tasks_library/integrated_tasks/`

## 主要工作流：`codex_task_builder/`（Node.js + TypeScript）

`codex_task_builder/` 基于 Codex SDK 生成 Harbor 风格的 `integrated_tasks`，并在发布前按任务执行 reviewer / 静态校验 /（可选）运行校验。

### 前置条件

- Node.js 18+ / `npm`
- 本机可用的 `codex` CLI
- 模型认证环境变量：`OPENAI_API_KEY`
- 如需运行校验：Docker（Windows 上通常需要 WSL2 + Docker Desktop）

### 安装依赖与类型检查

```bash
cd /home/levi/Harbor/codex_task_builder
npm install

npm run check
```

### 常用命令

```bash
# 扫描 source task 元信息与 skills
npm run inventory -- --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks

# 生成单个 source task 的 4-task family（默认 1 similar + 3 transfer）
npm run generate-family -- \
  --source-task-id 3d-scan-calc \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks

# 批量生成
export CODEX_TASK_BUILDER_MODEL=gpt-5.2
npm run batch -- \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks \
  --output-root /home/levi/Harbor/tasks_library/integrated_tasks \
  --limit 2 \
  --family-concurrency 2

# 对最近一次 scratch run 重新做 reviewer
npm run review -- \
  --source-task-id 3d-scan-calc \
  --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks
```

补充说明：

- scratch workspace：`/tmp/harbor-codex-task-builder/<run_id>/<source_task_id>/`
- 运行记录（manifest）：`codex_task_builder_runs/manifest.jsonl`（已在 `.gitignore` 中）
- 发布目录：`tasks_library/integrated_tasks/<source_task_id>/<derived_task_id>/`
- 工具不会删除任何目录，也不会覆盖已有同名任务目录（只会追加新任务）

> 注意：当前实现默认假设仓库路径为 `/home/levi/Harbor`。如果你把仓库放在其他路径，需要修改 `codex_task_builder/src/utils.ts` 里的 `REPO_ROOT`。

## 目录结构

- `tasks_library/skillsbench/tasks/`：上游 source tasks（包含 `environment/skills/**`）
- `tasks_library/integrated_tasks/`：生成后的 Harbor tasks
- `codex_task_builder/`：生成器（planner / writer / reviewer / validate / publish）
- `docs/`：设计文档与中文使用说明
- `guide.md`：研究背景与目标

## 可选：Python 依赖（实验脚本 / Harbor SDK）

仓库根目录提供 `requirements.lock` 用于锁定 Python 依赖（例如 `harbor` SDK、数据处理/实验脚本等）。如果你需要运行这些脚本，可用 `uv` 安装：

```bash
cd /home/levi/Harbor
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip sync requirements.lock
```

安全提醒：请用环境变量或 `.env` 管理 API Key 等敏感信息，避免写入代码或提交到 Git。

## 更多文档

- `docs/codex_task_builder_usage_zh.md`
- `docs/codex_sdk_full_task_builder_plan.md`
- `codex_task_builder/README.md`
