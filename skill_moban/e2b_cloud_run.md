# E2B 云端运行说明

本文档整理 `template_new` 在 E2B 云端跑 `codex + gpt-5.4` 对照实验的固定口径。

当前约定只使用你提供的新版 Codex 配置方法：

- Harbor 原生 `-e e2b`
- `harbor run`
- 通过 `HARBOR_CODEX_CONFIG_PATH` 把外置 `config.toml` 注入 Harbor 内部 Codex
- `with_skill` / `without_skill` 的唯一区别只来自 `environment/skills/` 及其对应的 runtime 剥离逻辑
- 模板 Dockerfile 不再预装 `@openai/codex`；Harbor 的 `codex` agent setup 会在 E2B runtime 内安装并执行 Codex CLI

补充约定：

- 最终要交付给用户的 `template_new` 源码里，不保留任何显式 skill 提示。
- README 里的对照数据，只能使用有效 trial：必须真正跑到 task-level，存在完整 agent 轨迹，并排除启动失败、BuildException、build cancelled 一类 trial。

## 1. 私有配置文件

私有变量保存在：

`/home/lenovo/skill/Harbor/skill_moban/.e2b_cloud_run.env`

这个文件已加入 `.gitignore`，用于保存：

- `E2B_API_KEY`
- `OPENAI_API_KEY`
- `CODEX_MODEL_PROVIDER`
- `CODEX_PROVIDER_BASE_URL`
- `HARBOR_MODEL`
- E2B 输出目录和 runtime 副本目录

统一加载方式：

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/.e2b_cloud_run.env
set +a
```

说明：`harbor run` 会走 `/mnt/e/tools/uv-bin/harbor` 对应的 uv tool 环境；不再用
`python3 -m harbor.cli.main run`，避免本机 `/usr/bin/python3` 与 Harbor tool venv
加载到不同的 Python/site-packages。

## 2. 生成 Harbor 用 Codex 配置

每次跑实验前，先根据 `.e2b_cloud_run.env` 生成一份临时 `config.toml`，然后导出
`HARBOR_CODEX_CONFIG_PATH`。

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/.e2b_cloud_run.env
set +a

TMP_CODEX_HOME="$(mktemp -d /tmp/codexzhongzhuan.XXXXXX)"
cat > "$TMP_CODEX_HOME/config.toml" <<EOF
model_provider = "$CODEX_MODEL_PROVIDER"
model = "$HARBOR_MODEL"
model_reasoning_effort = "$CODEX_REASONING_EFFORT"
disable_response_storage = $CODEX_DISABLE_RESPONSE_STORAGE
approvals_reviewer = "$CODEX_APPROVALS_REVIEWER"

approval_policy = "$CODEX_APPROVAL_POLICY"
sandbox_mode = "$CODEX_SANDBOX_MODE"
web_search = "$CODEX_WEB_SEARCH"
personality = "$CODEX_PERSONALITY"

[model_providers]
[model_providers.$CODEX_MODEL_PROVIDER]
name = "$CODEX_MODEL_PROVIDER"
wire_api = "responses"
base_url = "$CODEX_PROVIDER_BASE_URL"
env_key = "OPENAI_API_KEY"

[notice]
[notice.model_migrations]

"gpt-5.2" = "gpt-5.4"
EOF

export HARBOR_CODEX_CONFIG_PATH="$TMP_CODEX_HOME/config.toml"
```

实验结束后清理：

```bash
rm -rf "$TMP_CODEX_HOME"
unset HARBOR_CODEX_CONFIG_PATH
```

## 3. 生成 with/without runtime 副本

为了保持对照实验的唯一区别只来自 skill，先生成两份 runtime 副本：

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/.e2b_cloud_run.env
set +a

rm -rf "$E2B_RUNTIME_ROOT"
mkdir -p "$E2B_RUNTIME_ROOT"
cp -R /home/lenovo/skill/Harbor/skill_moban/<某template的类>/template_new \
  "$E2B_RUNTIME_ROOT/task_with_skills_e2b"
cp -R /home/lenovo/skill/Harbor/skill_moban/<某template的类>/template_new \
  "$E2B_RUNTIME_ROOT/task_without_skills_e2b"
rm -rf "$E2B_RUNTIME_ROOT/task_without_skills_e2b/environment/skills"

python3 - <<'PY'
from pathlib import Path

import os

dockerfile = Path(os.environ["E2B_RUNTIME_ROOT"]) / "task_without_skills_e2b/environment/Dockerfile"
text = dockerfile.read_text(encoding="utf-8")
lines = []

for line in text.splitlines():
    if line.startswith("COPY skills"):
        continue
    lines.append(line)

dockerfile.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
PY
```

说明：

- `with_skill` 运行包保留 `environment/skills/`，Dockerfile 里保留 `COPY skills ...`。
- `without_skill` 运行包删除 `environment/skills/`，并同步删除 Dockerfile 里的 `COPY skills ...`。
- 模板只需要覆盖 Harbor 当前会读取的 skill 路径，不需要再考虑 `/home/user` 或额外 agent 家目录。

## 4. 在 E2B 跑 Codex + GPT-5.4 对照实验

说明：

- 不再使用默认 provider 的 `OPENAI_BASE_URL`
- 统一用 `harbor run`
- Harbor 环境统一走原生 `-e e2b`
- Harbor 内部 Codex 通过 `HARBOR_CODEX_CONFIG_PATH` 读取外置配置
- 不需要在模板 Dockerfile 里写 `RUN npm install -g @openai/codex@0.120.0`

### with skill

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/.e2b_cloud_run.env
set +a

TMP_CODEX_HOME="$(mktemp -d /tmp/codexzhongzhuan.XXXXXX)"
cat > "$TMP_CODEX_HOME/config.toml" <<EOF
model_provider = "$CODEX_MODEL_PROVIDER"
model = "$HARBOR_MODEL"
model_reasoning_effort = "$CODEX_REASONING_EFFORT"
disable_response_storage = $CODEX_DISABLE_RESPONSE_STORAGE
approvals_reviewer = "$CODEX_APPROVALS_REVIEWER"

approval_policy = "$CODEX_APPROVAL_POLICY"
sandbox_mode = "$CODEX_SANDBOX_MODE"
web_search = "$CODEX_WEB_SEARCH"
personality = "$CODEX_PERSONALITY"

[model_providers]
[model_providers.$CODEX_MODEL_PROVIDER]
name = "$CODEX_MODEL_PROVIDER"
wire_api = "responses"
base_url = "$CODEX_PROVIDER_BASE_URL"
env_key = "OPENAI_API_KEY"

[notice]
[notice.model_migrations]

"gpt-5.2" = "gpt-5.4"
EOF

export HARBOR_CODEX_CONFIG_PATH="$TMP_CODEX_HOME/config.toml"

harbor run \
  -p "$E2B_RUNTIME_ROOT/task_with_skills_e2b" \
  -a "$HARBOR_AGENT" \
  -m "$HARBOR_MODEL" \
  -e e2b \
  --ae "OPENAI_API_KEY=$OPENAI_API_KEY" \
  --agent-timeout-multiplier "$AGENT_TIMEOUT_MULTIPLIER" \
  --force-build \
  -n "$HARBOR_CONCURRENCY" \
  --job-name template-new-with-skills-e2b-YYYYMMDD \
  -o "$HARBOR_JOBS_DIR" \
  --debug

rm -rf "$TMP_CODEX_HOME"
unset HARBOR_CODEX_CONFIG_PATH
```

### without skill

```bash
source /mnt/e/tools/harbor-env.sh
set -a
source /home/lenovo/skill/Harbor/skill_moban/.e2b_cloud_run.env
set +a

TMP_CODEX_HOME="$(mktemp -d /tmp/codexzhongzhuan.XXXXXX)"
cat > "$TMP_CODEX_HOME/config.toml" <<EOF
model_provider = "$CODEX_MODEL_PROVIDER"
model = "$HARBOR_MODEL"
model_reasoning_effort = "$CODEX_REASONING_EFFORT"
disable_response_storage = $CODEX_DISABLE_RESPONSE_STORAGE
approvals_reviewer = "$CODEX_APPROVALS_REVIEWER"

approval_policy = "$CODEX_APPROVAL_POLICY"
sandbox_mode = "$CODEX_SANDBOX_MODE"
web_search = "$CODEX_WEB_SEARCH"
personality = "$CODEX_PERSONALITY"

[model_providers]
[model_providers.$CODEX_MODEL_PROVIDER]
name = "$CODEX_MODEL_PROVIDER"
wire_api = "responses"
base_url = "$CODEX_PROVIDER_BASE_URL"
env_key = "OPENAI_API_KEY"

[notice]
[notice.model_migrations]

"gpt-5.2" = "gpt-5.4"
EOF

export HARBOR_CODEX_CONFIG_PATH="$TMP_CODEX_HOME/config.toml"

harbor run \
  -p "$E2B_RUNTIME_ROOT/task_without_skills_e2b" \
  -a "$HARBOR_AGENT" \
  -m "$HARBOR_MODEL" \
  -e e2b \
  --ae "OPENAI_API_KEY=$OPENAI_API_KEY" \
  --agent-timeout-multiplier "$AGENT_TIMEOUT_MULTIPLIER" \
  --force-build \
  -n "$HARBOR_CONCURRENCY" \
  --job-name template-new-without-skills-e2b-YYYYMMDD \
  -o "$HARBOR_JOBS_DIR" \
  --debug

rm -rf "$TMP_CODEX_HOME"
unset HARBOR_CODEX_CONFIG_PATH
```

如果本地终端容易因为长时间滚动输出被杀，推荐把 Harbor 输出重定向到文件：

```bash
harbor run \
  ... \
  --debug \
  > "$HARBOR_JOBS_DIR/<job-name>.stdout.log" 2>&1
```

这样可以在不影响 job 执行的前提下，后读 `stdout.log`、`job.log` 和 `result.json`。

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
- `started_at`
- `finished_at`
- `agent_execution.started_at`
- `agent_execution.finished_at`

有效对照实验的推荐判定口径：

- `result.json` 里 `n_trials = 1` 且 `n_errors = 0`
- trial 级 `result.json` 存在
- `verifier_result.rewards.reward` 已落盘
- 有完整 `agent/` 目录与轨迹文件

不计入 README 统计的常见情况：

- `BuildException`
- `build was cancelled`
- 只有 job 级目录、没有 trial 级 `result.json`
- Harbor/本地 shell 被杀，导致结果未完整落盘

如果 Harbor 还没落出 `result.json`，先看 agent 轨迹：

```bash
sed -n '1,260p' "$HARBOR_JOBS_DIR/<job-name>/<trial-name>/agent/command-1/stdout.txt"
```

如果需要 verifier 细节：

```bash
sed -n '1,260p' "$HARBOR_JOBS_DIR/<job-name>/<trial-name>/verifier/pytest-output.txt"
```
