你接手了一个失败的复用 GitHub Actions 工作流调用。

仓库在 `/workspace/repo`，失败上下文放在 `/workspace/ci_artifacts`。

请完成下面两件事：

1. 先阅读 caller workflow、reusable workflow 和多个失败 job 日志，定位这次矩阵调用失败的共同根因。
   把调查结论写到 `/workspace/reports/workflow-contract-findings.md`。
   这份报告至少需要说明：
   - 哪些 matrix job 失败了
   - 失败发生在 caller workflow 的哪个调用位置
   - 关键报错指向了哪个 input 或矩阵参数契约不一致
   - 根因对应到仓库里的哪个 workflow 文件
   - 哪个下游 job 因此被阻塞，以及你准备如何修复
2. 修改 `/workspace/repo` 中必要的工作流或脚本，让本地契约检查脚本通过：
   - `/workspace/repo/scripts/run_reusable_contract_check.sh`

完成后请自行运行一次复现脚本确认修复已经生效，并保留你的调查报告。
