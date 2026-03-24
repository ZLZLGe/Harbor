你需要修复一个仓库内失效的 GitHub Actions Python 测试流水线。

仓库位于 `/workspace/scoreboard-service`。
项目已经提供了 `pyproject.toml` 和 `uv.lock`，但当前 `.github/workflows/python-ci.yml`
仍然沿用旧的 `pip`/`requirements.txt` 安装方式，导致 CI 不能稳定跑通。

请只修改让流水线恢复所必需的内容，目标输出文件是 `.github/workflows/python-ci.yml`。

Step 1: 先分析当前工作流为什么失效。
把你的分析和修改计划写到 `/workspace/scoreboard-service/ci-notes/plan.txt`。

Step 2: 更新 `.github/workflows/python-ci.yml`，
让它基于仓库现有的项目配置与 lockfile 安装依赖，并用该环境执行测试。

Step 3: 运行 `python scripts/local_ci_check.py`，
确认这份工作流对应的本地 CI 检查可以通过。
