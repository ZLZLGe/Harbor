# 任务说明（认证会话治理）

你需要读取认证事件数据，按照固定门禁规则计算风险，并输出标准化 JSON 结果。

## 输入
- 输入文件：`/app/workspace/input/auth_events.csv`
- 字段定义：
  - `flow_id`：认证流标识
  - `session_ttl_min`：会话有效期，单位分钟
  - `mfa_enabled`：是否启用 MFA，取值 `yes` 或 `no`
  - `cookie_secure`：Cookie 是否启用 Secure，取值 `yes` 或 `no`
  - `cookie_httponly`：Cookie 是否启用 HttpOnly，取值 `yes` 或 `no`
  - `token_rotation_days`：令牌轮换周期，单位天
  - `failed_logins_24h`：24 小时内失败登录次数

## 输出
- 主输出文件：`/app/workspace/output/auth_gate.json`
- JSON 根结构必须为：
  - `summary`
  - `flows`
- `summary` 字段：
  - `total_flows`
  - `blocked_flows`
- `flows` 中每个对象字段顺序固定为：
  - `flow_id`
  - `status`
  - `risk_level`
  - `risk_score`
  - `reasons`

## 评分规则
- `mfa_enabled = no`：`+40`，原因代码 `mfa_missing`
- `cookie_secure = no`：`+20`，原因代码 `cookie_not_secure`
- `cookie_httponly = no`：`+20`，原因代码 `cookie_not_httponly`
- `token_rotation_days > 30`：`+10`，原因代码 `rotation_too_slow`
- `failed_logins_24h >= 10`：`+10`，原因代码 `bruteforce_risk`
- `session_ttl_min > 1440`：`+10`，原因代码 `session_ttl_too_long`

## 风险与门禁规则
1. `risk_level`：
   - `risk_score >= 60` -> `high`
   - `risk_score >= 30` 且 `< 60` -> `medium`
   - 其余 -> `low`
2. `status`：
   - 若 `mfa_enabled = no`，或 `cookie_secure = no`，或 `cookie_httponly = no`，或 `risk_score >= 60`，则为 `blocked`
   - 否则若 `risk_score >= 30`，则为 `review`
   - 否则为 `pass`
3. `reasons` 为按规则触发顺序收集的原因代码列表。
4. `flows` 必须按 `flow_id` 升序排序。
5. 输出必须稳定、可重复，不允许引入随机性。

## 禁止事项
- 不允许修改输入文件。
- 不允许输出额外主结果文件替代 `auth_gate.json`。
- 不允许依赖联网数据或外部服务。
