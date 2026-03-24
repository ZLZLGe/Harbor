# Transfer - 审计 Python 备份恢复归档处理改动

## 审计范围

- 仓库：`/home/levi/Harbor/codex_task_builder_runs/scratch/20260319193954-fix-erlang-ssh-cve-find-bugs-sfgy4m/fix-erlang-ssh-cve/drafts/python-backup-find-bugs-transfer-tar-symlink/environment/workspace/backup-restore-review`
- 基线分支：`main`（`7837a4e`）
- 审计分支：`levi/tar-restore-hardening`（`4c52184`）
- 已完整阅读文件：
  - `docs/review-brief.md`
  - `src/backup_restore/archive_restore.py`
  - `src/backup_restore/restore_job.py`
  - `tests/test_restore.py`

## 已确认问题

### 1. High - `TarInfo.linkname` 完全未校验，恶意符号链接成员仍可把恢复树指向任意外部路径

- 位置：`src/backup_restore/archive_restore.py:9`、`src/backup_restore/archive_restore.py:12`、`src/backup_restore/archive_restore.py:30`
- 问题：新的过滤逻辑只规范化并检查了 `member.name`，没有校验 `member.linkname`。因此归档里即便把成员名伪装成 `tenant/current` 这样的安全相对路径，也仍然可以让符号链接目标指向 `/etc` 或 `../../../../var/spool/cron`。
- 证据：`_is_safe_member_name()` 只基于 `member.name` 做绝对路径和 `..` 检查；`extract_archive()` 在成员通过这个检查后直接调用 `tar.extract(member, path=restore_root, set_attrs=False)`。对于 `issym()` / `islnk()` 成员，`tarfile` 会按照原始 `linkname` 落盘，分支里没有任何额外约束。
- 影响：攻击者可以先在恢复目录里植入一个指向外部目录的符号链接，为后续普通文件成员或清单回放阶段制造“看起来仍在 restore_root 内，实际已跳出目录”的写入路径。
- 覆盖缺口：测试只新增了 `test_rejects_absolute_member` 和 `test_rejects_dotdot_member`，再加上正常场景的 `test_restores_regular_files`；没有任何用例验证 `rejects_external_symlink_target` 或 `rejects_hardlink_target`。

### 2. High - 清单回放阶段会跟随已解包的符号链接写入标记文件，最终形成任意路径覆盖

- 位置：`src/backup_restore/restore_job.py:15`、`src/backup_restore/restore_job.py:17`、`src/backup_restore/restore_job.py:18`、`src/backup_restore/restore_job.py:21`
- 问题：`apply_manifest()` 对每个清单条目只做了 `lstrip("/")`，随后直接把 `restore_root / relative_path` 当作目标目录创建并写入 `.restore-state.json`，既不做 `resolve()` 边界检查，也不阻止父目录是符号链接。
- 证据：`restore_snapshot()` 先执行 `extract_archive()`，再读取归档内的 `manifest.json` 并调用 `apply_manifest()`。结合上一个问题，攻击者可以先在归档中放入 `customers/acme -> /root/.ssh` 之类的符号链接，再让清单包含 `{"path": "customers/acme", ...}`；`target_dir.mkdir(..., exist_ok=True)` 和后续 `marker_path.write_text(...)` 都会沿这个符号链接在恢复根目录外写入文件。
- 影响：只要恢复进程对目标路径有写权限，就可能覆盖外部目录中的状态文件、定时任务、密钥材料或应用配置，风险已经不再局限于“恢复目录被污染”。
- 覆盖缺口：`test_manifest_marker_written` 只覆盖了普通目录下生成标记文件的 happy path，没有制造符号链接目录，也没有验证清单回放时的目录边界。

## 已检查但未发现新增问题

- 普通成员名的绝对路径和 `..` 路径穿越在 `src/backup_restore/archive_restore.py` 里确实有显式拒绝，这一层拦截本身是生效的。
- 当前 diff 没有引入新的网络入口、命令执行或动态导入逻辑；主要风险集中在 tar 成员到文件系统写入的映射。
- 现有测试中的正常恢复路径仍然能覆盖常规文件恢复和清单标记写入的基础流程，问题不在“功能完全失效”，而在边界条件被遗漏。

## 核查清单

- 注入：本次 diff 没看到新的命令注入或模板注入点。
- 认证/授权：该服务不是鉴权逻辑改动，本次审计重点不在访问控制。
- 路径约束：确认存在 2 条可证实的越界写入链路，分别落在 tar 成员解包和清单回放阶段。
- DoS：未看到新的无界读取或无限循环，当前更关键的是任意路径写入。
- 测试覆盖：已有测试只验证普通成员名过滤和正常恢复路径，没有覆盖符号链接目标与符号链接父目录。

## 无法完全验证的部分

- 我没有实际构造 tar 包运行恢复流程，所以没有对具体 Python 版本下的落盘细节做动态复现；不过从 `main...HEAD` 的完整代码路径、`tarfile` 的调用方式以及测试缺口来看，上述两条问题链都已经能在静态审计层面确认成立。
