你接手了一个已经失败的 Python PR 测试矩阵。

仓库在 `/workspace/repo`，失败上下文放在 `/workspace/ci_artifacts`。

请完成下面两件事：

1. 先阅读 PR 背景和失败日志，定位这次 GitHub Actions PR 失败的根因。
   把诊断结论写到 `/workspace/reports/pr-triage.md`。
   这份报告至少需要说明：
   - 哪些 matrix job 失败了
   - 关键报错或受影响测试
   - 根因对应到仓库里的哪个文件或函数
   - 你准备如何修复
2. 修改 `/workspace/repo` 中必要的代码或配置，让本地矩阵复现脚本通过：
   - `/workspace/repo/scripts/run_pr_matrix.sh`

完成后请自行运行一次复现脚本确认修复已经生效，并保留你的诊断报告。
