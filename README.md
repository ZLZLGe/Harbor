# Harbor

## 环境复现（推荐使用 uv）

### 前置条件
- Python：`3.12`（本仓库当前环境在 `3.12.3` 下验证）
- 已安装 `uv`

### 一键复现依赖
在仓库根目录执行：

```bash
# 创建虚拟环境（放在 .venv/，不提交到 Git）
uv venv --python 3.12 .venv

# 激活虚拟环境（Linux/macOS）
source .venv/bin/activate

# 严格按锁定版本安装依赖
uv pip sync requirements.lock
```

### 不使用 uv（可选）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
```

## 依赖锁文件

依赖版本锁定在 `requirements.lock`。

## Skill-to-Task 数据管线

仓库现在包含一个 `harbor_skill_pipeline/`，用于从现有 `tasks_library/skillsbench/tasks/**/environment/skills` 扫描 skill 输入，并自动生成 Harbor 格式任务。默认粒度是“单个源任务下的整个 `environment/skills` 目录”；也可以切换成 `environment/skills/<skill_name>` 这种单个 skill 子目录粒度。生成阶段只喂技能范围内的 markdown 文档，以及源任务的白名单参考文件：`task.toml`、`instruction.md`、`environment/Dockerfile`、`solution/solve.sh`、`tests/test.sh`、`tests/test_outputs.py`。

### 主要命令

```bash
source .venv/bin/activate

# 扫描 skill occurrence
python -m harbor_skill_pipeline inventory -c configs/skill_to_task.example.toml

# 跑一个真实模型的小样本 smoke
export RIGHT_CODES_API_KEY=...
python -m harbor_skill_pipeline batch -c configs/skill_to_task.smoke.toml --limit 1 --match 3d-scan-calc
```

更完整的目录结构、验证阶段和批量运行方式见 `docs/skill_to_task_pipeline.md`。
