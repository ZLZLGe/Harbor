# 任务说明（平台 Secrets 与 mTLS 控制包）

你需要读取平台控制项输入，生成统一的控制包 JSON 输出。

## 输入
- 输入文件：`/app/workspace/input/platform_controls.json`
- 输入结构固定为：
  ```json
  {
    "services": [
      {
        "name": "...",
        "namespace": "...",
        "mtls": "...",
        "secret_store": "...",
        "network_policy": "...",
        "cert_expiry_days": 0
      }
    ]
  }
  ```
- `services` 是服务对象数组。
- 每个服务对象至少包含以下字段：
  - `name`
  - `namespace`
  - `mtls`
  - `secret_store`
  - `network_policy`
  - `cert_expiry_days`

## 输出
- 输出文件：`/app/workspace/output/control_bundle.json`
- 输出结构必须为：
  ```json
  {
    "summary": {"total_services": 0, "failed_services": 0},
    "services": [
      {
        "name": "...",
        "namespace": "...",
        "status": "pass|fail",
        "rotation_priority": "normal|urgent",
        "violations": []
      }
    ]
  }
  ```

## 处理规则
1. 对每个服务按以下规则生成 `violations`，顺序固定为：
   - `mtls != "required"` 时加入 `mtls_missing`
   - `secret_store` 不在 `{ "vault", "1password", "keyvault" }` 时加入 `weak_secret_store`
   - `network_policy != "strict"` 时加入 `network_open`
   - `cert_expiry_days < 15` 时加入 `cert_rotation_urgent`
2. `status` 规则：
   - `violations` 非空时输出 `fail`
   - `violations` 为空时输出 `pass`
3. `rotation_priority` 规则：
   - `cert_expiry_days < 15` 时输出 `urgent`
   - 否则输出 `normal`
4. `summary.total_services` 等于输入中的服务总数。
5. `summary.failed_services` 等于 `status = "fail"` 的服务数量。
6. `services` 数组必须按 `name` 升序排序。
7. 输出必须稳定可重现；禁止依赖随机值、时间变化、联网数据或人工交互。
8. `violations` 必须输出数组，即使为空也必须是 `[]`。

## 禁止事项
- 不允许修改输入文件。
- 不允许输出额外顶层字段。
- 不允许改变字段名大小写。
- 不允许把空数组写成 `null`。
