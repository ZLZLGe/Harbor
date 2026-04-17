# E2B 云端运行说明

本文档整理 `template_new` 在 E2B 云端跑 `oracle` 与 `codex + gpt-5.4` 对照实验的固定口径。

## 1. 私有配置文件

私有配置保存在：

`/home/lenovo/skill/Harbor/skill_moban/debugging/template_new/.e2b_cloud_run.env`

这个文件已加入 `.gitignore`，用于保存：

- `E2B_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `HARBOR_MODEL`
- `HARBOR_ENV_IMPORT_PATH`
- E2B 运行输出目录和 runtime 副本目录

执行前统一加载：

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/debugging/template_new/.e2b_cloud_run.env
set +a
export PYTHONPATH="/home/lenovo${PYTHONPATH:+:$PYTHONPATH}"
```

说明：

- 这里不直接使用 Harbor 原生 `-e e2b`。
- 当前任务的 `environment/Dockerfile` 依赖完整 build context，E2B 需要走补丁环境
  `harbor_e2b_context_patch:PatchedE2BEnvironment`，否则模板构建可能拿不到完整 `COPY` 上下文。

## 2. 在 E2B 跑 Oracle

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/debugging/template_new/.e2b_cloud_run.env
set +a
export PYTHONPATH="/home/lenovo${PYTHONPATH:+:$PYTHONPATH}"

harbor run \
  -p /home/lenovo/skill/Harbor/skill_moban/debugging/template_new \
  -a oracle \
  --environment-import-path "$HARBOR_ENV_IMPORT_PATH" \
  --force-build \
  -n "$HARBOR_CONCURRENCY" \
  --job-name template-new-oracle-e2b-YYYYMMDD \
  -o "$HARBOR_JOBS_DIR" \
  --debug
```

结果读取：

- job 配置：`$HARBOR_JOBS_DIR/<job-name>/config.json`
- job 总结果：`$HARBOR_JOBS_DIR/<job-name>/result.json`
- trial 结果：`$HARBOR_JOBS_DIR/<job-name>/<trial-name>/result.json`
- verifier 输出：`$HARBOR_JOBS_DIR/<job-name>/<trial-name>/verifier/pytest-output.txt`
- reward：`$HARBOR_JOBS_DIR/<job-name>/<trial-name>/verifier/reward.txt`

## 3. 生成 E2B 对照实验 runtime 副本

为了保持 with/without 的唯一区别只来自 skill，先生成两份 runtime 副本：

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/debugging/template_new/.e2b_cloud_run.env
set +a

rm -rf "$E2B_RUNTIME_ROOT"
mkdir -p "$E2B_RUNTIME_ROOT"
cp -R /home/lenovo/skill/Harbor/skill_moban/debugging/template_new \
  "$E2B_RUNTIME_ROOT/task_with_skills_e2b"
cp -R /home/lenovo/skill/Harbor/skill_moban/debugging/template_new \
  "$E2B_RUNTIME_ROOT/task_without_skills_e2b"
rm -rf "$E2B_RUNTIME_ROOT/task_without_skills_e2b/environment/skills"

python3 - <<'PY'
from pathlib import Path

dockerfile = Path("/home/lenovo/.tmp_debugging_validation/runtime_e2b_current/task_without_skills_e2b/environment/Dockerfile")
text = dockerfile.read_text(encoding="utf-8")
lines = []
skip_browser_testing_install = False

for line in text.splitlines():
    if "COPY skills/browser-testing" in line:
        continue
    if "RUN npm install --prefix /opt/browser-testing" in line:
        skip_browser_testing_install = True
        continue
    if skip_browser_testing_install:
        if line.startswith("ENV PLAYWRIGHT_BROWSERS_PATH="):
            skip_browser_testing_install = False
            lines.append('ENV PLAYWRIGHT_BROWSERS_PATH=""')
            continue
        continue
    if line.startswith('ENV PATH="/opt/browser-testing/node_modules/.bin:${PATH}"'):
        lines.append('ENV PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"')
        continue
    lines.append(line)

dockerfile.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
PY
```

## 4. 在 E2B 跑 Codex + GPT-5.4 对照实验

### with skill

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/debugging/template_new/.e2b_cloud_run.env
set +a
export PYTHONPATH="/home/lenovo${PYTHONPATH:+:$PYTHONPATH}"

harbor run \
  -p "$E2B_RUNTIME_ROOT/task_with_skills_e2b" \
  -a "$HARBOR_AGENT" \
  -m "$HARBOR_MODEL" \
  --ae "OPENAI_API_KEY=$OPENAI_API_KEY" \
  --ae "OPENAI_BASE_URL=$OPENAI_BASE_URL" \
  --ak "reasoning_effort=$CODEX_REASONING_EFFORT" \
  --environment-import-path "$HARBOR_ENV_IMPORT_PATH" \
  --agent-timeout-multiplier "$AGENT_TIMEOUT_MULTIPLIER" \
  --force-build \
  -n "$HARBOR_CONCURRENCY" \
  --job-name template-new-with-skills-e2b-YYYYMMDD \
  -o "$HARBOR_JOBS_DIR" \
  --debug
```

### without skill

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/debugging/template_new/.e2b_cloud_run.env
set +a
export PYTHONPATH="/home/lenovo${PYTHONPATH:+:$PYTHONPATH}"

harbor run \
  -p "$E2B_RUNTIME_ROOT/task_without_skills_e2b" \
  -a "$HARBOR_AGENT" \
  -m "$HARBOR_MODEL" \
  --ae "OPENAI_API_KEY=$OPENAI_API_KEY" \
  --ae "OPENAI_BASE_URL=$OPENAI_BASE_URL" \
  --ak "reasoning_effort=$CODEX_REASONING_EFFORT" \
  --environment-import-path "$HARBOR_ENV_IMPORT_PATH" \
  --agent-timeout-multiplier "$AGENT_TIMEOUT_MULTIPLIER" \
  --force-build \
  -n "$HARBOR_CONCURRENCY" \
  --job-name template-new-without-skills-e2b-YYYYMMDD \
  -o "$HARBOR_JOBS_DIR" \
  --debug
```

## 5. 结果读取口径

先看 job 级：

```bash
cat "$HARBOR_JOBS_DIR/<job-name>/result.json"
```

再看 task-level：

```bash
find "$HARBOR_JOBS_DIR/<job-name>" -maxdepth 2 -type d
cat "$HARBOR_JOBS_DIR/<job-name>/<trial-name>/result.json"
```

关键字段：

- `verifier_result.rewards.reward`
- `agent_result.n_input_tokens`
- `agent_result.n_output_tokens`
- `started_at`
- `finished_at`
- `environment_setup`
- `agent_execution`

如果需要 verifier 细节：

```bash
sed -n '1,260p' "$HARBOR_JOBS_DIR/<job-name>/<trial-name>/verifier/pytest-output.txt"
```
