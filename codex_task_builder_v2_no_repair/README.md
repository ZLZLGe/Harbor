# codex_task_builder_v2_no_repair

`codex_task_builder_v2_no_repair/` 是基于 `codex_task_builder_v2/` 拆出来的无修复基线版本，用来做对照实验。

这套实现保留了 planner、writer、reviewer、static validate、Harbor Oracle runtime、publish/quarantine 整条流水线，但彻底移除了 repair 机制：

- reviewer 失败：直接进入 quarantine
- static validate 失败：直接进入 quarantine
- runtime 失败：直接进入 quarantine
- 不再存在 `--max-repair-rounds`
- 不再执行多轮 cycle；每个任务只跑固定的 `cycle=0`

补充文档：

- `TASK_BUILDER_FLOW.md`：按源码整理的完整执行流

## 目录约定

- source root: `/home/levi/Harbor/tasks_library/skillsbench/tasks`
- raw runs root: `/home/levi/Harbor/codex_task_builder_v2_no_repair_runs/raw`
- quarantine root: `/home/levi/Harbor/codex_task_builder_v2_no_repair_runs/quarantine`
- final tasks root: `/home/levi/Harbor/tasks_library/auto_harbor_tasks_v2_no_repair`

最终任务目录结构固定为：

```text
<final-root>/<source-task-id>/<scope>/<task-name>
```

- `scope`
  - `all` 模式固定为 `all-skills`
  - `per-skill` 模式固定为 skill `dirName`
- `task-name`
  - `similar1`, `similar2`, ...
  - `transfer1`, `transfer2`, ...

## 当前能力

- 支持 `all` / `per-skill` 两种技能作用域
- 支持 `--similar-count` 与 `--transfer-count` 控制 family 规模
- 支持 `--concurrency` 做 family 级并发
- 每个 family workspace 会同时提供：
  - `source_task/`
  - `builder_refs/harbor/`
- family 内部仍然会做：
  - planner 规划
  - writer 写任务
  - reviewer 审稿
  - static validate
  - Harbor Oracle runtime validate
- raw / final / quarantine 三层产物分离
- `plan.json` 会保留在 draft 和最终发布目录里
- 最终 Harbor 任务的用户可见描述强制使用英文
- static validate 会检查：
  - `plan.json`
  - task metadata
  - instruction/task metadata 英文约束
  - `environment/skills` 与当前 `all` / `per-skill` scope 的精确一致性
  - 固定 `[environment]` 资源配额
  - Dockerfile 公共镜像策略
- runtime validate 默认走 Harbor 官方 Oracle：
  - `harbor run -p <task_dir> -a oracle -e daytona --force-build --jobs-dir <logs_dir> --job-name <job_name>`
- 每次 runtime 尝试都会生成唯一的 `cycle-0-attempt-1` 目录
- 发布阶段不做删除，只从草稿目录选择性复制 Harbor 任务必需文件

## Codex 默认权限

SDK 当前默认使用：

- `sandboxMode: "danger-full-access"`
- `approvalPolicy: "never"`
- `networkAccessEnabled: true`

如果需要缩权限，可以通过环境变量覆盖：

- `CODEX_TASK_BUILDER_SANDBOX_MODE=workspace-write`
- `CODEX_TASK_BUILDER_NETWORK_ACCESS=0`

## 安装与检查

安装依赖：

```bash
cd /home/levi/Harbor/codex_task_builder_v2_no_repair
npm install
```

类型检查：

```bash
cd /home/levi/Harbor/codex_task_builder_v2_no_repair
npm run check
```

运行测试：

```bash
cd /home/levi/Harbor/codex_task_builder_v2_no_repair
npm run test:prompts
npm run test:validate
```

## 命令示例

扫描 source task：

```bash
cd /home/levi/Harbor/codex_task_builder_v2_no_repair
npm run inventory -- --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks
```

生成单个 source task 的 family：

```bash
cd /home/levi/Harbor/codex_task_builder_v2_no_repair
export DAYTONA_API_KEY="your_daytona_api_key_here"
npm run generate-family -- \
  --source-task-id setup-fuzzing-py \
  --skill-mode per-skill \
  --target-skill-dir fuzzing \
  --similar-count 1 \
  --transfer-count 1 \
  --concurrency 1
```

批量生成：

```bash
cd /home/levi/Harbor/codex_task_builder_v2_no_repair
export DAYTONA_API_KEY="your_daytona_api_key_here"
npm run batch -- \
  --skill-mode per-skill \
  --similar-count 1 \
  --transfer-count 2 \
  --concurrency 2 \
  --limit 10 \
  --final-root /home/levi/Harbor/tasks_library/auto_harbor_tasks_v2_no_repair
```

重新 review 最近一次 workspace：

```bash
cd /home/levi/Harbor/codex_task_builder_v2_no_repair
npm run review -- \
  --source-task-id citation-check \
  --scope-slug all-skills
```

## 参数说明

下面只解释当前 CLI 已实现的参数；真实行为以 [src/cli.ts](/home/levi/Harbor/codex_task_builder_v2_no_repair/src/cli.ts) 为准。

### `inventory`

- `--source-root`
  - source task 根目录。
  - 默认值：`/home/levi/Harbor/tasks_library/skillsbench/tasks`

### `generate-family` / `batch` 通用参数

- `--source-root`
  - source task 根目录。
  - 默认值：`/home/levi/Harbor/tasks_library/skillsbench/tasks`

- `--source-task-id`
  - 只处理某一个 source task。
  - 不传时会扫描 `source-root` 下全部 source tasks，并生成对应的可执行 unit。
  - `generate-family` 也支持不传，但那样行为会更接近串行版 `batch`。

- `--skill-mode`
  - 技能作用域模式。
  - 可选值：`all`、`per-skill`
  - 默认值：`all`
  - `all`：一个 source task 只生成一个 family，保留全部 shipped skills。
  - `per-skill`：一个 source task 按 skill 拆成多个 family，每个 family 只保留一个 skill。

- `--target-skill-dir`
  - 只处理指定 skill `dirName` 对应的 family。
  - 主要在 `per-skill` 模式下使用。

- `--similar-count`
  - 每个 family 最终应保留多少个 `similar` 任务。
  - 默认值：`1`
  - 不能小于 `0`，并且不能和 `transfer-count` 同时为 `0`。
  - 重复执行时，会先扫描 `final-root`，只补缺失的 `similarN`。

- `--transfer-count`
  - 每个 family 最终应保留多少个 `transfer` 任务。
  - 默认值：`3`
  - 不能小于 `0`，并且不能和 `similar-count` 同时为 `0`。
  - 重复执行时，会先扫描 `final-root`，只补缺失的 `transferN`。

- `--concurrency`
  - family 级并发数。
  - 默认值：
    - `generate-family`：`1`
    - `batch`：`2`
  - 含义是“同时处理多少个 generation unit”。
  - 注意：单个 family 内部的 runtime validate 仍然是串行执行的。

- `--raw-root`
  - 原始 workspace/runs 根目录。
  - 默认值：`/home/levi/Harbor/codex_task_builder_v2_no_repair_runs/raw`
  - planner、writer、reviewer、static/runtime 校验产物都会先落在这里。
  - 单个 family workspace 下会生成：
    - `source_task/`
    - `builder_refs/harbor/`
    - `drafts/`
    - `artifacts/`
  - 每次 runtime 尝试会落在：
    - `<raw-root>/<run-id>/<source-task-id>/<scope>/artifacts/runtime/<task-id>/cycle-0-attempt-1/`

- `--final-root`
  - 最终发布任务根目录。
  - 默认值：`/home/levi/Harbor/tasks_library/auto_harbor_tasks_v2_no_repair`
  - planner / writer / reviewer 会读取这里已发布的同 family 任务，尽量避免和历史任务撞题。

- `--output-root`
  - `--final-root` 的兼容别名。
  - 如果同时传了 `--final-root` 和 `--output-root`，以 `--final-root` 为准。

- `--quarantine-root`
  - 未通过最终校验的任务落盘目录。
  - 默认值：`/home/levi/Harbor/codex_task_builder_v2_no_repair_runs/quarantine`
  - reviewer/static/runtime 任一阶段失败，都会复制到这里。
  - `quarantine-root` 不计入“当前 family 已满足的任务数量”。

- `--limit`
  - 最多处理多少个生成单元。
  - 默认值：不限制。
  - 主要给 `batch` 用；如果不传 `source-task-id`，程序会先过滤掉已经在 `final-root` 达到目标数量的 family，再对剩余 unit 截断。

### `review`

- `--source-task-id`
  - 要重新 review 的 source task。
  - 必填。

- `--raw-root`
  - 查找最近一次 workspace 的 raw 根目录。
  - 默认值：`/home/levi/Harbor/codex_task_builder_v2_no_repair_runs/raw`

- `--scope-slug`
  - 可选，用来限制只看某个 scope。
  - 例如：
    - `all-skills`
    - `citation-management`

## 相关环境变量

- `DAYTONA_API_KEY`
  - 当 runtime 环境是 `daytona` 时必须提供。

- `CODEX_TASK_BUILDER_RUNTIME_ENV`
  - runtime 校验后端。
  - 可选值：`daytona`、`docker`
  - 默认值：`daytona`

- `CODEX_TASK_BUILDER_MODEL`
  - 可选，覆盖 Codex SDK 使用的模型。

- `CODEX_TASK_BUILDER_SANDBOX_MODE`
  - 可选，覆盖 SDK 的 sandbox 模式。
  - 当前实现默认是 `danger-full-access`；如果设为 `workspace-write`，会切回较小权限。

- `CODEX_TASK_BUILDER_NETWORK_ACCESS`
  - 可选，是否允许 Codex 访问网络。
  - 默认行为等价于开启；设为 `0` 时关闭。

- `CODEX_PATH`
  - 可选，覆盖默认 `codex` 可执行文件路径。

## 重要说明

- 这个目录是无修复基线，不会自动进行 repair。
- 失败任务不会被删除，只会复制到 quarantine。
- `review-result.round-0.json`、`runtime.cycle-0.json` 这类命名仍然保留，是为了和原版产物结构尽量一致。
- Daytona Oracle 超过 5 分钟是正常的；当前实现不会用固定 5 分钟超时主动杀掉运行。
