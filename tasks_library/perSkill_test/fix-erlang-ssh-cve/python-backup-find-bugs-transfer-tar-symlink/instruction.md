`/app/workspace/backup-restore-review` 里有一个本地 Git 仓库，当前审计分支是 `levi/tar-restore-hardening`，基线分支是 `main`。

这个分支声称给 Python 备份恢复服务补上了 tar 归档恢复能力，并且已经拦住了归档成员路径穿越。

请审计 `main...HEAD` 的改动，确认这套解包与恢复逻辑是否仍然允许恶意归档成员或符号链接把文件写到恢复目录之外。只记录已经能从代码路径、分支 diff 和现有测试覆盖变化中证实的问题。

把结论写到 `/app/workspace/reports/transfer-backup-archive-findings.md`，使用中文。报告至少包含：

- 审计范围与已完整阅读的文件
- 已确认问题：严重性、文件/行号、问题描述、证据、影响、以及为什么现有测试没有覆盖到
- 已检查但未发现新增问题的要点
- 无法完全验证的部分与原因

不要修改仓库源码，也不要输出到其他路径。
