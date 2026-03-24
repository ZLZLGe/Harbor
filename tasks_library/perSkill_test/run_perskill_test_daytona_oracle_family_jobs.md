# run_perskill_test_daytona_oracle_family_jobs.sh 使用说明

## 作用

这个脚本用于把：

```text
/home/levi/Harbor/tasks_library/perSkill_test
```

按 family 分组执行 Harbor 的 Daytona Oracle 校验，而不是把整个 `perSkill_test` 扁平化成一个大 dataset 一次跑完。

它会按 family 名字母序依次处理：

```text
perSkill_test/
  family-a/
    task-1/
    task-2/
  family-b/
    task-3/
```

每个 family 都会单独执行一次：

```bash
harbor run -p <family_dir> -a oracle -e daytona ...
```

和现有 unpublished family 脚本不同，这个版本：

- 只面向 `perSkill_test`
- 不做 pass/fail 任务复制
- 不写 `classified_root`
- 所有 Harbor jobs 都集中到一个 batch 根目录里

## 脚本路径

```bash
/home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh
```

## 输出位置

假设本次 batch 名是：

```text
Daytona_20260324_1800
```

那么 Harbor jobs 会集中写到：

```text
/home/levi/Harbor/tasks_library/perSkill_test/jobs/Daytona_20260324_1800
```

其中每个 family 的实际结果目录是：

```text
/home/levi/Harbor/tasks_library/perSkill_test/jobs/Daytona_20260324_1800/<family-name>
```

例如：

```text
/home/levi/Harbor/tasks_library/perSkill_test/jobs/Daytona_20260324_1800/jax-computing-basics
```

统一报表会写到：

```text
/home/levi/Harbor/tasks_library/perSkill_test/jobs/Daytona_20260324_1800/reports
```

## 默认参数

默认值如下：

```bash
AGENT_NAME=oracle
ENV_NAME=daytona
BATCH_NAME=perSkill-test-daytona-oracle-family-<timestamp>
START_FAMILY=<从第一个 family 开始>
N_FAMILIES=<全部选中的 family>
N_CONCURRENT=2
MAX_MEMORY_MB=4096
MAX_STORAGE_MB=10240
```

任务输入根目录固定为：

```bash
/home/levi/Harbor/tasks_library/perSkill_test
```

jobs 根目录固定为：

```bash
/home/levi/Harbor/tasks_library/perSkill_test/jobs
```

## 资源过滤规则

脚本在真正执行 Harbor 之前，会先解析每个 task 的有效资源配置。

默认只跑：

- `memory_mb <= 4096`
- `storage_mb <= 10240`

资源字段兼容两套写法：

- 新字段：`[environment].memory_mb`、`[environment].storage_mb`
- 旧字段：`[environment].memory`、`[environment].storage`

如果 task 没显式写资源字段，脚本按 Harbor 默认值补齐：

- `memory_mb = 2048`
- `storage_mb = 10240`

旧字段支持 `K / M / G` 单位，换算为 MB：

- `memory = "4G"` 会按 `4096` 处理
- `storage = "5G"` 会按 `5120` 处理

超出限制的 task 不会运行，但会记录到报表里。

## 最基本用法

先进入 Harbor 仓库目录：

```bash
cd /home/levi/Harbor
```

然后执行：

```bash
bash /home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh
```

## 常用示例

只预览，不真正运行：

```bash
bash /home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh \
  --dry-run
```

从某个 family 开始：

```bash
bash /home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh \
  --start-family jax-computing-basics
```

只跑前 5 个 family：

```bash
bash /home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh \
  --n-families 5
```

限制 Daytona 并发为 2：

```bash
bash /home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh \
  --n-concurrent 2
```

显式指定 batch 名：

```bash
bash /home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh \
  --batch-name Daytona_20260324_1800
```

放宽资源上限：

```bash
bash /home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh \
  --max-memory-mb 8192 \
  --max-storage-mb 20480
```

同时指定起点、family 数和并发：

```bash
bash /home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh \
  --start-family jax-computing-basics \
  --n-families 3 \
  --n-concurrent 2 \
  --batch-name Daytona_20260324_1800
```

透传额外 Harbor 参数：

```bash
bash /home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh \
  --n-concurrent 2 \
  -- --verbose
```

## 执行流程

脚本实际会按下面顺序工作：

1. 扫描 `perSkill_test` 顶层 family，自动忽略 `jobs/`
2. 如果传了 `--start-family`，从该 family 开始
3. 如果传了 `--n-families`，只保留前 N 个 family
4. 对每个 family 解析 task 的有效资源
5. 超过 `--max-memory-mb` 或 `--max-storage-mb` 的 task 直接跳过
6. 如果某个 family 过滤后一个 task 都不剩，状态记为 `skipped_no_eligible_tasks`
7. 否则执行一次：

```bash
harbor run \
  -p <family_dir> \
  -a oracle \
  -e daytona \
  --force-build \
  --jobs-dir /home/levi/Harbor/tasks_library/perSkill_test/jobs/<batch-name> \
  --job-name <family-name> \
  --n-concurrent <N> \
  --task-name <task-1> \
  --task-name <task-2> ...
```

8. 每个 family 跑完后，脚本会解析对应目录下的 `result.json`
9. 最后生成统一报表

## Oracle 判定规则

脚本会读取：

```text
/home/levi/Harbor/tasks_library/perSkill_test/jobs/<batch-name>/<family-name>/*/result.json
```

判定规则如下：

1. 只认 `result.json.task_name`
2. `exception_info != null` 记为 fail
3. 否则读取 `verifier_result.rewards.reward`
4. 只有 `reward == 1.0` 记为 pass
5. 缺失 `result.json`、缺失 reward、reward 不等于 `1.0` 都记为 fail
6. 同一 task 如果有多个结果，取 `result.json` 修改时间最新的一份

## 报表文件

统一报表目录是：

```text
/home/levi/Harbor/tasks_library/perSkill_test/jobs/<batch-name>/reports
```

其中会生成：

- `family_runs.tsv`
- `skipped_resource_limits.tsv`
- `classification.tsv`
- `summary.json`

用途分别是：

- `family_runs.tsv`：记录每个 family 的总 task 数、过滤后运行数、Harbor 退出码、是否真正执行
- `skipped_resource_limits.tsv`：记录哪些 task 因为 memory/storage 超限被跳过
- `classification.tsv`：记录每个实际运行 task 的 pass/fail、reward、异常类型、失败原因、结果路径
- `summary.json`：记录本次 batch 的总览统计

## 注意事项

脚本会把 `jobs/<batch-name>` 当作本次运行的唯一输出根目录。

如果：

```text
/home/levi/Harbor/tasks_library/perSkill_test/jobs/<batch-name>
```

已经存在，脚本会直接报错退出，不会覆盖旧结果。

脚本要求当前 shell 里能直接找到：

- `harbor`
- `python3`

如果某个 family 的 `harbor run` 非零退出，脚本最后会整体退出 1。

如果有 task 被判定为 fail，脚本最后也会整体退出 1。

## 推荐排查顺序

如果执行失败，优先检查：

1. `harbor` 命令是否能直接运行
2. `python3` 是否在 `PATH` 中
3. `--start-family` 是否精确命中真实 family 名
4. `--batch-name` 对应的 jobs 目录是否已存在
5. `--dry-run` 打印出来的 family 和命令是否符合预期
6. `reports/classification.tsv` 里的 `failure_reason` 和 `exception_type`
