# Similar - 审计 Erlang SSH Channel 状态机加固补丁

## 审计范围

- 仓库：`/home/levi/Harbor/codex_task_builder_runs/scratch/20260319193954-fix-erlang-ssh-cve-find-bugs-sfgy4m/fix-erlang-ssh-cve/drafts/otp-ssh-find-bugs-similar-channel-state-audit/environment/workspace/otp-ssh-review`
- 基线分支：`main`（`d0e9347`）
- 审计分支：`levi/ssh-channel-hardening`（`11812c4`）
- 已完整阅读文件：
  - `docs/review-brief.md`
  - `lib/ssh/src/ssh_connection.erl`
  - `lib/ssh/src/ssh_server_channel.erl`
  - `lib/ssh/test/ssh_channel_state_SUITE.erl`

## 已确认问题

### 1. High - `subsystem` 仍可沿未认证路径进入子系统启动逻辑

- 位置：`lib/ssh/src/ssh_connection.erl:31`、`lib/ssh/src/ssh_server_channel.erl:26`、`lib/ssh/src/ssh_server_channel.erl:53`、`lib/ssh/src/ssh_server_channel.erl:79`
- 问题：新的认证前拦截只在 `ssh_connection:handle_msg/4` 中阻断了 `exec` 和 `shell`，没有覆盖 `subsystem`。同时，`ssh_server_channel:new/1` 把新 channel 直接初始化为 `phase = session_ready`，而 `start_subsystem/4` 只检查 `phase`，完全不检查 `#ssh.authenticated`。
- 证据：攻击者只要先发送 `CHANNEL_OPEN` 建立 session channel，就会得到一个 `phase = session_ready` 的 channel 记录；随后 `subsystem` 请求会从 `ssh_connection.erl:38-42` 落到 `ssh_server_channel.erl:53-58`，再由 `ssh_server_channel.erl:79-80` 直接进入子系统启动分支。
- 影响：这个分支声称解决认证前 channel 消息问题，但实际上只是把 pre-auth RCE 的入口从 `exec` 收窄到了 `subsystem`，未认证客户端仍然可以在 userauth 之前触发子系统路径。
- 覆盖缺口：测试只新增了 `preauth_exec_disconnects/1`（`lib/ssh/test/ssh_channel_state_SUITE.erl:5-12`），没有任何对应的 `preauth_subsystem_disconnects` 用例，所以这条路径没有被验证。

### 2. Medium - 认证后的普通 `shell` 会话被错误地要求必须先申请 PTY

- 位置：`lib/ssh/src/ssh_server_channel.erl:46`、`lib/ssh/src/ssh_server_channel.erl:74`、`lib/ssh/test/ssh_channel_state_SUITE.erl:5`
- 问题：`start_shell/3` 现在只接受 `phase = pty_ready` 的 channel，其他情况一律走 `reply_failure/2`。这把“先开 shell，再决定是否申请 PTY”的正常认证后会话也判成失败。
- 证据：基线分支上的测试名是 `authenticated_shell_without_pty_works/1`，说明之前明确覆盖了“登录后直接 shell”场景；当前分支把它替换成 `authenticated_shell_after_pty_works/1`，同时 `start_shell/3` 的成功分支只剩 `#channel{phase = pty_ready}`，因此无 PTY 的 shell 会话必然回归。
- 影响：自动化客户端、受限 shell 或不需要终端的会话在认证成功后会收到 channel request failure，属于正常业务回归，不只是测试改名。
- 覆盖缺口：测试文件保留了 “after pty” 的 happy path，但删掉了 “without pty” 的兼容性用例，因此这类回归不会被现有分支测试发现。

## 已检查但未发现新增问题

- 认证前 `exec` 请求现在会在 `lib/ssh/src/ssh_connection.erl:31-36` 被直接断开，这一条拦截本身是生效的。
- 认证后的 `exec` 路径仍然要求 `#ssh.authenticated = true` 才会命中 `ssh_server_channel:handle_request/3` 的 `exec` 分支，当前 diff 没有额外放宽这里的条件。
- `pty-req` 的新增处理只会在 `#ssh.authenticated = true` 时更新 channel phase，本身没有再打开新的未认证入口。

## 核查清单

- 注入：未在本次 diff 中看到新的命令拼接或字符串注入点，主要风险仍然来自状态机边界。
- 认证/授权：确认存在 1 条未认证 `subsystem` 路径，以及 1 个认证后正常 shell 回归。
- 会话状态：`phase` 的语义被错误复用，既表示 channel 已创建，又被拿来代表认证后可进入子系统，导致边界混淆。
- DoS：未看到新的循环或无界分配逻辑；这次更核心的问题是状态机错误，而不是资源消耗。
- 测试覆盖：新增覆盖只验证了 `exec` 的 pre-auth 拦截，没有覆盖 `subsystem`，同时删掉了无 PTY shell 的兼容性测试。

## 无法完全验证的部分

- 我没有运行完整 Erlang/OTP 集成测试，也没有启动真实 SSH 服务复现实包交互；以上结论基于 `main...HEAD` diff、当前分支完整代码路径和测试覆盖变化，证据已经足以确认这两个问题在本地分支上是真实存在的。
