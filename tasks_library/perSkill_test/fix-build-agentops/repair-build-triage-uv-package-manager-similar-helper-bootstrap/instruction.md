你需要修复一个仓库内的 Python 构建排障辅助流程。

仓库位于 `/opt/build-triage-helper`。
失败副本位于 `/opt/build-triage-helper/workspace/failed_copy`。
补丁素材位于 `/opt/build-triage-helper/patch_bundle`。

Step 1: 先分析失败副本为什么无法通过复现脚本。
把你的分析和执行计划写到 `/opt/build-triage-helper/workspace/analysis/plan.txt`。

Step 2: 在仓库中实现 `tools/fetch_patch_bundle.py`。
这个脚本需要读取补丁素材，生成标准 unified diff 补丁文件，并把补丁写到
`/opt/build-triage-helper/workspace/failed_copy/patches/`。

Step 3: 在 `/opt/build-triage-helper-bootstrap` 初始化一个临时 Python 项目，
安装运行该脚本所需的少量依赖，然后从这个临时项目里运行
`/opt/build-triage-helper/tools/fetch_patch_bundle.py`。
生成补丁后，把这些补丁应用到失败副本。

Step 4: 运行 `bash /opt/build-triage-helper/run_repro.sh`，
确保复现脚本通过。
