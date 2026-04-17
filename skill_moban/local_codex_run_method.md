# 本地 Codex 对比实验方法

## 目的

在本地 Docker 环境中，用完全相同的 Codex 模型与运行参数，分别对以下两套任务运行一次：

- `with skills`：`/home/lenovo/.tmp_debugging_validation/runtime/task_with_skills`
- `without skills`：`/home/lenovo/.tmp_debugging_validation/runtime/task_without_skills`

两者的唯一区别应当是任务环境里是否包含 `environment/skills/` 及对应 Dockerfile 复制逻辑；不得通过额外 prompt、显式提醒或人工干预制造差异。

## Solver 可见范围

本任务需要明确区分“仓库里的维护材料”和“Codex 真正求解时能看到的输入”：

- Codex 在任务容器里直接可见的是 `/app` 源码和运行环境本身
- `/root` 不再暴露任何 incident 摘要、console 摘要或 HAR / trace 线索
- `/services/api-simulator` 存在于环境中，但属于隐藏 baseline，不允许编辑
- 仓库侧的维护材料只用于审计与复盘，不会被 Codex 在求解时直接浏览
- 因此，若无 skill 也能通过，默认先归因于它利用了容器内已有的浏览器执行能力，而不是“看到了提示文件”

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

配置文件：`/home/lenovo/skill/Harbor/skill_moban/local_codex_run_config.env`

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
source /home/lenovo/skill/Harbor/skill_moban/local_codex_run_config.env
set +a
"$HARBOR_WRAPPER" "$WITH_SKILLS_TASK_PATH" codex-with-skills-formal-20260406
```

### 2. without skills

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/local_codex_run_config.env
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

`benchmark_report.md` 只保留结论性内容，不再写执行流水账。固定章节如下：

- 数据质量
- 任务有效性
- Oracle 质量
- Verifier 设计与合理性
- 多模态验证
- skill 与任务强相关性
- 结论
