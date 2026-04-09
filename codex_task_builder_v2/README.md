# codex_task_builder_v2

`codex_task_builder_v2/` 是新的 Harbor 任务自动构造流水线实现，目标是把 planner、writer、reviewer、Oracle 校验和 repair 串成一条自动闭环，而不是只停留在“生成后再手动改 Oracle 失败任务”。

补充文档：

- `TASK_BUILDER_FLOW.md`：按源码梳理的完整造任务流程说明
- `FINAL_TASK_REQUIREMENTS.md`：当前对最终生成 Harbor 任务的要求汇总

## 目录约定

- source root: `/home/levi/Harbor/tasks_library/skillsbench/tasks`
- runs root: `/home/levi/Harbor/codex_task_builder_v2_runs`
- raw runs root: `/home/levi/Harbor/codex_task_builder_v2_runs/raw`
- quarantine root: `/home/levi/Harbor/codex_task_builder_v2_runs/quarantine`
- final tasks root: `/home/levi/Harbor/tasks_library/auto_harbor_tasks`

最终任务目录结构固定为：

```text
<final-root>/<source-task-id>/<scope>/<task-name>
```

- `scope`:
  - `all` 模式固定为 `all-skills`
  - `per-skill` 模式固定为 skill `dirName`
- `task-name`:
  - `similar1`, `similar2`, ...
  - `transfer1`, `transfer2`, ...

## 当前能力

- 支持 `all` / `per-skill` 两种技能作用域
- 支持 `--similar-count` 与 `--transfer-count` 自定义 family 规模
- 支持 `--concurrency` 进行 family 级并发
- 每个 family workspace 会同时提供：
  - `source_task/`
  - `builder_refs/harbor/`
- family 内部按顺序执行 Oracle 校验
- Oracle 失败后自动把 reviewer/static/runtime 问题和完整 Harbor runtime 日志回灌给 Codex repair
- runtime 失败不再区分 infra retry 和 repair retry；每个 cycle 每个任务只跑一次 runtime，失败后统一进入 repair 流
- raw / final / quarantine 三层产物分离
- `plan.json` 会保留在 draft 和最终任务目录里
- 最终 Harbor 任务的用户可见描述强制使用英文
- static validate 会检查：
  - `plan.json`
  - task metadata
  - instruction/task metadata 英文约束
  - `environment/skills` 与当前 `all` / `per-skill` scope 的精确一致性
  - 固定 `[environment]` 资源配额
  - Dockerfile 公共镜像策略
- runtime validate 默认走 Harbor 官方 Oracle：
  - `harbor run -p <task_dir> -a oracle -e e2b --force-build --jobs-dir <logs_dir> --job-name <job_name>`
- 每次 runtime 尝试都会生成唯一的 `cycle-<n>-attempt-<m>` 目录，避免 repair 后复用旧 Oracle 结果
- 发布阶段不做删除，只从草稿目录选择性复制 Harbor 任务必需文件

## Codex 权限

SDK 默认使用：

- `sandboxMode: "danger-full-access"`
- `approvalPolicy: "never"`
- `networkAccessEnabled: true`

如果你确实想收回一点权限，可以通过环境变量覆盖：

- `CODEX_TASK_BUILDER_SANDBOX_MODE=workspace-write`
- `CODEX_TASK_BUILDER_NETWORK_ACCESS=0`

## 命令

安装依赖：

```bash
cd /home/levi/Harbor/codex_task_builder_v2
npm install
```

类型检查：

```bash
npm run check
```

扫描 source task：

```bash
cd /home/levi/Harbor/codex_task_builder_v2
npm run inventory -- --source-root /home/levi/Harbor/tasks_library/skillsbench/tasks
```

生成单个 source task：

```bash
cd /home/levi/Harbor/codex_task_builder_v2
export E2B_API_KEY="your_e2b_api_key_here"
export OPENAI_API_KEY="your_openai_api_key_here"
npm run generate-family -- \
  --source-task-id setup-fuzzing-py \
  --skill-mode per-skill \
  --similar-count 1 \
  --transfer-count 1 \
  --max-repair-rounds 2 \
  --concurrency 3
```

批量生成：

```bash
cd /home/levi/Harbor/codex_task_builder_v2
export E2B_API_KEY="your_e2b_api_key_here"
export OPENAI_API_KEY="your_openai_api_key_here"
npm run batch -- \
  --skill-mode per-skill \
  --similar-count 1 \
  --transfer-count 2 \
  --concurrency 2 \
  --limit 10 \
  --final-root /home/levi/Harbor/tasks_library/auto_harbor_tasks
```

重新 review 最近一次 workspace：

```bash
cd /home/levi/Harbor/codex_task_builder_v2
npm run review -- \
  --source-task-id citation-check \
  --scope-slug all-skills
```

## 参数说明

下面只解释当前 CLI 已实现的参数；这些参数的真实行为以 [src/cli.ts](/home/levi/Harbor/codex_task_builder_v2/src/cli.ts) 为准。

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
  - 不传时会扫描 `source-root` 下的多个 source task；这个场景主要给 `batch` 用。

- `--skill-mode`
  - 技能作用域模式。
  - 可选值：`all`、`per-skill`
  - 默认值：`all`
  - `all`：一个 family 保留该 source task 的全部 shipped skills。
  - `per-skill`：把 source task 按 skill 拆成多个 family，每个 family 只保留一个 skill。

- `--target-skill-dir`
  - 只处理某个指定的 skill `dirName`。
  - 只在 `per-skill` 模式下有实际筛选意义。

- `--similar-count`
  - 每个 family 最终应保留多少个 `similar` 任务。
  - 默认值：`1`
  - 不能小于 `0`，并且不能和 `transfer-count` 同时为 `0`。
  - 重复执行时，会先扫描 `final-root`，如果当前 family 还没达到这个数量，就只补齐缺失的 `similarN`。

- `--transfer-count`
  - 每个 family 最终应保留多少个 `transfer` 任务。
  - 默认值：`3`
  - 不能小于 `0`，并且不能和 `similar-count` 同时为 `0`。
  - 重复执行时，会先扫描 `final-root`，如果当前 family 还没达到这个数量，就只补齐缺失的 `transferN`。

- `--concurrency`
  - family 级并发数。
  - 默认值：
    - `generate-family`：`1`
    - `batch`：`2`
  - 含义是“同时处理多少个 source-task/skill 输入单元”。
  - 注意：单个 family 内部的 Oracle 校验仍然是串行执行的。

- `--raw-root`
  - 原始 workspace/runs 根目录。
  - 默认值：`/home/levi/Harbor/codex_task_builder_v2_runs/raw`
  - planner、writer、reviewer、runtime 日志、skill-effect 对照日志、repair 记录都会先落在这里。
  - 单个 family workspace 下会生成：
    - `source_task/`
    - `builder_refs/harbor/`
    - `drafts/`
    - `artifacts/`
  - 每次 Oracle 尝试会落在：
    - `<raw-root>/<run-id>/<source-task>/<scope>/artifacts/runtime/<task>/cycle-<cycle>-attempt-<attempt>/`
  - 每次 skill-effect 对照会落在：
    - `<raw-root>/<run-id>/<source-task>/<scope>/artifacts/skill_effect/<task>/cycle-<cycle>-attempt-<attempt>/with_skill`
    - `<raw-root>/<run-id>/<source-task>/<scope>/artifacts/skill_effect/<task>/cycle-<cycle>-attempt-<attempt>/no_skill`

- `--runs-root`
  - phase 级 manifest 和 run summary 的根目录。
  - 默认值：`/home/levi/Harbor/codex_task_builder_v2_runs`
  - 如果显式传入，`manifest.jsonl` 和 `<run-id>.json` 会写到这里。
  - 如果没传，但 `--raw-root` 是自定义值，则默认取 `dirname(raw-root)` 作为 `runs-root`，这样 smoke/实验产物会自动收拢到同一个根目录。

- `--final-root`
  - 最终发布任务根目录。
  - 默认值：`/home/levi/Harbor/tasks_library/auto_harbor_tasks`
  - planner / writer / reviewer 会直接读取这里已经发布的同 family 任务，避免和历史任务撞题。

- `--output-root`
  - `--final-root` 的兼容别名。
  - 如果同时传了 `--final-root` 和 `--output-root`，以 `--final-root` 为准。

- `--quarantine-root`
  - 未通过最终校验的任务落盘目录。
  - 默认值：`/home/levi/Harbor/codex_task_builder_v2_runs/quarantine`
  - `quarantine-root` 只用于保留失败任务，不计入“当前 family 已满足的任务数量”。

- `--max-repair-rounds`
  - 单个任务最多允许 Codex 做多少轮修复。
  - 默认值：`2`
  - 适用于 reviewer/static 失败、Oracle runtime 失败，以及 skill-effect gate 失败。
  - 每做一轮 repair，后续 Oracle 会使用新的 `jobs-dir` 和 `job-name` 真正重跑。

- `--skip-skill-effect-gate`
  - 可选 flag。
  - 默认不传，即默认开启 skill-effect gate。
  - 传入后会跳过“Oracle 通过后再真实对照跑 with_skill / no_skill”的阶段。
  - 只有在你明确只想保留旧行为时才建议使用。

- `--skill-effect-model`
  - 控制 skill-effect gate 里真实对照使用的 agent model。
  - 默认值：`openai/gpt-5.4`
  - 当前实现固定用 `codex` agent，区别只在 model 名称。

- `--limit`
  - 最多处理多少个生成单元。
  - 默认值：不限制
  - 主要给 `batch` 用；如果不传 `source-task-id`，会先过滤掉已经在 `final-root` 达到目标数量的 family，再对剩余 unit 截断。

### `review`

- `--source-task-id`
  - 要重新 review 的 source task。
  - 必填。
  - 默认面向当前版本代码生成的 workspace；如果本地还保留旧格式的历史 runs，建议先清理 `/home/levi/Harbor/codex_task_builder_v2_runs`，或至少不要再对这些旧 runs 执行 `review`。

- `--raw-root`
  - 查找最近一次 workspace 的 raw 根目录。
  - 默认值：`/home/levi/Harbor/codex_task_builder_v2_runs/raw`

- `--scope-slug`
  - 可选，用来指定只看某个 scope。
  - 例如：
    - `all-skills`
    - `citation-management`

## 相关环境变量

- `E2B_API_KEY`
  - 当 runtime 环境是 `e2b` 时必须提供。

- `DAYTONA_API_KEY`
  - 当 runtime 环境是 `daytona` 时必须提供。

- `OPENAI_API_KEY`
  - 当启用默认 skill-effect gate 时必须提供。
  - 这部分不是给 planner/writer/reviewer 的 SDK 调用，而是给 Harbor `codex` 实跑 with_skill / no_skill 对照使用。

- `OPENAI_BASE_URL`
  - 可选。
  - 如果要走兼容 OpenAI API 的代理或中转地址，可以在这里指定；skill-effect gate 会透传给 Harbor `codex` 运行。

- `CODEX_TASK_BUILDER_RUNTIME_ENV`
  - runtime 校验后端。
  - 可选值：`e2b`、`daytona`、`docker`
  - 默认值：`e2b`

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

- 不会修改旧目录 `/home/levi/Harbor/codex_task_builder`
- Harbor Oracle runtime 超过 5 分钟是正常的；当前实现不会用固定 5 分钟超时去杀掉运行
- repair prompt 会显式告诉 Codex：把完整 runtime 日志目录当作主入口，而不只是盯住 `harbor-run.log`/`result.json`
- runtime 失败统一进入 repair；当前实现不再单独维护 `infra retry`
- 默认开启 skill-effect gate：Oracle 通过后，还会真实跑一轮 `with_skill` 和一轮临时派生的 `no_skill`
- 当前 no-skill 派生策略是只删除 Dockerfile 里的 `COPY skills ...` 行，不删除 `environment/skills/` 目录
- skill-effect gate 只接受两类结果：
  - `with_skill_pass__no_skill_fail`
  - `with_skill_fail__no_skill_fail`
- 以下两类结果会直接回 repair，而不是发布：
  - `with_skill_pass__no_skill_pass`
  - `with_skill_fail__no_skill_pass`
- 发布或隔离时，会额外镜像一份到 bucket 目录，便于后续统计：
  - `<final-root>/_skill_effect_buckets/<bucket>/<source-task-id>/<scope>/<task-name>`
  - `<quarantine-root>/_skill_effect_buckets/<bucket>/<source-task-id>/<scope>/<task-name>`
- 发布阶段不执行删除操作；final/quarantine 目录都是通过选择性复制生成
- 最终发布目录只复制：
  - `task.toml`
  - `instruction.md`
  - `plan.json`
  - `environment/`
  - `solution/`
  - `tests/`
- 重复执行 `generate-family` / `batch` 时，会先扫描 `final-root`，只补齐当前 family 缺失的 `similarN` / `transferN`
- 已满足数量的 family 会在加载阶段直接跳过，不会进入 planner / writer / reviewer / oracle
- planner / writer / reviewer 会直接读取 `final-root` 下同 family 已发布任务，不依赖额外人工整理的上下文文件
- 如果 final 或 quarantine 目标目录已存在，当前实现会跳过复制，不覆盖、不删除，也不会因此报错
- `quarantine-root` 不参与“任务数量是否已满足”的判断；只有 `final-root` 中的任务会被视为已发布完成
- 当前“是否已发布完成”的判断基于 `final-root` 下目录是否存在，而不是对目录内容做完整性校验
- 如果发布阶段中途被打断，导致 `final-root` 或 `quarantine-root` 留下残缺目录，需要人工确认并清理对应目录后再重跑；否则后续补齐流程可能把它误判为已存在任务
- `manifest.jsonl` 和 `<run-id>.json` 不再固定绑定全局目录；它们默认跟随 `runs-root`，而 `runs-root` 在自定义 `raw-root` 时会默认跟随 `dirname(raw-root)`
- Dockerfile 不允许使用本地私有镜像或私有 registry
- family 级并发只影响“同时处理多少个输入单元”；单个 family 内部的 Oracle 仍然按任务顺序串行执行

## 本地校验

```bash
cd /home/levi/Harbor/codex_task_builder_v2
npm run check
npm run test:prompts
npm run test:validate
```
