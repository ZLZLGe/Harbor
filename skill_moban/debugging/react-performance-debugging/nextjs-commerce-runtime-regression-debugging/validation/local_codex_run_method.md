# 本地 Codex 对比实验方法

## 目的

在本地 Docker 环境中，用完全相同的 Codex 模型与运行参数，分别对以下两套任务运行一次：

- `with skills`：`/home/lenovo/.tmp_debugging_validation/runtime/task_with_skills`
- `without skills`：`/home/lenovo/.tmp_debugging_validation/runtime/task_without_skills`

两者的唯一区别应当是任务环境里是否包含 `environment/skills/` 及对应 Dockerfile 复制逻辑；不得通过额外 prompt、显式提醒或人工干预制造差异。

## Solver 可见范围

本任务需要明确区分“仓库里的审计资产”和“Codex 真正求解时能看到的输入”：

- Codex 在任务容器里直接可见的是 `/app` 源码与 `/root/*` 证据文件
- `/root/*` 由 `environment/Dockerfile` 在构建镜像时生成
- `/services/api-simulator` 存在于环境中，但属于隐藏 baseline，不允许编辑
- 仓库侧的 `materials/` 只是 provenance / audit 留档，不会被 Codex 在求解时直接浏览
- 因此，若无 skill 也能通过，默认先归因于它利用了容器内已有的浏览器执行能力，而不是“看到了仓库资产目录”

## 前置条件

1. 启动 Docker Desktop，并确保当前 WSL 发行版已经接入 Docker。
2. `source /mnt/e/tools/harbor-env.sh`
3. 校验 Harbor 可用：

```bash
source /mnt/e/tools/harbor-env.sh
harbor --version
docker ps
```

## 固定配置

配置文件：`validation/local_codex_run_config.env`

核心固定项：

- 模型：`gpt-5.4`
- 推理强度：`reasoning_effort=high`
- 最大轮数：`100`
- agent 超时倍率：`2`
- 不传 `prompt_template_path`
- 统一通过 Harbor docker 环境运行

## 正式运行命令

### 1. with skills

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/debugging/react-performance-debugging/nextjs-commerce-runtime-regression-debugging/validation/local_codex_run_config.env
set +a
"$HARBOR_WRAPPER" "$WITH_SKILLS_TASK_PATH" codex-with-skills-formal-20260406
```

### 2. without skills

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/debugging/react-performance-debugging/nextjs-commerce-runtime-regression-debugging/validation/local_codex_run_config.env
set +a
"$HARBOR_WRAPPER" "$WITHOUT_SKILLS_TASK_PATH" codex-without-skills-formal-20260406
```

## 结果读取位置

### with skills

- 作业目录：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-with-skills-formal-20260406`
- trial 目录：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-with-skills-formal-20260406/task_with_skills__p8e6W6H`
- 总结果：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-with-skills-formal-20260406/result.json`
- trial 结果：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-with-skills-formal-20260406/task_with_skills__p8e6W6H/result.json`
- verifier 输出：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-with-skills-formal-20260406/task_with_skills__p8e6W6H/verifier/pytest-output.txt`
- agent 轨迹：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-with-skills-formal-20260406/task_with_skills__p8e6W6H/agent/codex.txt`

### without skills

- 作业目录：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-without-skills-formal-20260406`
- 总结果：`/home/lenovo/.tmp_debugging_validation/runtime/codex_runs/codex-without-skills-formal-20260406/result.json`
- trial 结果：查看同目录下 `task_without_skills__*/result.json`
- verifier 输出：查看同目录下 `task_without_skills__*/verifier/pytest-output.txt`
- agent 轨迹：查看同目录下 `task_without_skills__*/agent/codex.txt`

## 口径检查

正式对比前必须确认：

1. `with skills` 的 `agent/command-1/command.txt` 中没有 `prompt_template_path` 或其他显式提醒注入。
2. `without skills` 同样只保留任务原始 instruction。
3. 两轮都使用同一模型、同一 wrapper、同一 turns 与 timeout 参数。
4. `with skills` 与 `without skills` 的任务目录差异只来自 `environment/skills/` 和对应 Dockerfile。

## 报告填充规则

从两轮 `result.json`、trial `result.json`、`verifier/pytest-output.txt`、`agent/codex.txt` 中提取以下内容写入 `benchmark_report.md`：

- Agent 结果：通过率、reward、执行时间
- Skills 影响：通过率差值、reward 差值、执行时间差值
- 失败分析：逐轮失败测试、期望与实际、根因、轨迹证据路径

如果某轮通过，则失败分析中应明确写“本轮无失败用例”，并保留 verifier 通过证据路径。
