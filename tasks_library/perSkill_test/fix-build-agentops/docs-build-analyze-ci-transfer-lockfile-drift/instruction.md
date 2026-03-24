你接手了一个失败的文档站点 CI 构建。

仓库在 `/workspace/repo`，失败上下文放在 `/workspace/ci_artifacts`。

请完成下面两件事：

1. 先阅读工作流和失败日志，定位这次文档站点构建失败的根因。
   把调查结论写到 `/workspace/reports/docs-build-investigation.md`。
   这份报告至少需要说明：
   - 哪些 job 失败了
   - 失败发生在哪个步骤
   - 关键报错指向了哪个依赖或锁文件问题
   - 根因对应到仓库里的哪个文件
   - 你准备如何修复
2. 修改 `/workspace/repo` 中必要的文件，让本地文档 CI 复现脚本通过：
   - `/workspace/repo/scripts/run_docs_ci.sh`

完成后请自行运行一次复现脚本确认修复已经生效，并保留你的调查报告。
