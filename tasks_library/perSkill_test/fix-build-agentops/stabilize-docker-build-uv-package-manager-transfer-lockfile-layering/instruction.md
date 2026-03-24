你需要修复一个仓库内不稳定的 Python 镜像构建流程。

仓库位于 `/workspace/incident-digest`。
项目已经提供了项目元数据、lockfile 和本地 vendored 依赖，但当前 `Dockerfile`
仍然先复制整个仓库，再导出临时 requirements 文件并调用 `pip install`，
导致依赖层缓存经常失效，也让构建流程不够稳定。

请只修改恢复该镜像构建所必需的内容，目标输出文件是 `Dockerfile`。

Step 1: 先分析当前镜像构建为什么不稳定。
把你的分析和修改计划写到 `/workspace/incident-digest/notes/docker-plan.txt`。

Step 2: 更新 `/workspace/incident-digest/Dockerfile`，
让它满足下面这些要求：
- 在镜像里第一次调用 `uv` 之前，先显式安装 `curl`，再运行官方安装脚本安装 `uv`，并用 `ENV PATH="/root/.local/bin:$PATH"` 让后续层能直接调用该命令。
- 先复制 `pyproject.toml`、`uv.lock` 和 `vendor/`，把依赖层与应用源码分开。
- 依赖层必须使用 `uv sync --frozen --no-install-project --no-dev`，不要再导出临时 requirements 文件，也不要调用 `pip install`。
- 把应用源码的复制步骤放在依赖层之后。
- 容器启动后应运行仓库现有的应用入口，并输出 `digest::container-ready`。
- 生成的 `Dockerfile` 必须是语法有效的镜像配方。

Step 3: 运行 `python tools/check_recipe.py`，
确认这份镜像配方满足本地检查。

Step 4: 如果环境里可以使用 `docker`，再执行一次 `docker build`，并验证生成的容器启动后会打印 `digest::container-ready`。
