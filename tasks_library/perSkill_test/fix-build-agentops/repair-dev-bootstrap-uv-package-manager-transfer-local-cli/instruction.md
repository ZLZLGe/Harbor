你需要修复一个仓库内失效的本地开发引导脚本。

仓库位于 `/workspace/dev-bootstrap-station`。
项目已经提供了 `.python-version`、`pyproject.toml` 和一个本地 CLI 模块，但当前
`scripts/bootstrap_env.sh` 仍然手动创建虚拟环境、硬编码解释器并直接依赖入口命令，
导致开发者很难一条命令启动成功。

请只修改恢复引导流程所必需的内容，目标输出文件是 `scripts/bootstrap_env.sh`。

Step 1: 先分析当前引导脚本为什么失效。
把你的分析和修改计划写到 `/workspace/dev-bootstrap-station/notes/bootstrap-plan.txt`。

Step 2: 更新 `/workspace/dev-bootstrap-station/scripts/bootstrap_env.sh`，
让它使用仓库约定的 Python 版本创建开发环境，并通过同一套环境运行本地 CLI，
生成 `var/bootstrap_report.txt`。

Step 3: 运行 `python tools/check_bootstrap.py`，
确认本地引导检查通过。
