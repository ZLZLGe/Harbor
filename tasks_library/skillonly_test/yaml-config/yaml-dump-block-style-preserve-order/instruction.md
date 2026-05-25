将 `/root/input/deployment_payload.json` 转换为 YAML，并写入 `/root/outputs/generated_config.yaml`。

输入 JSON 表示一次车队夜航部署的数据载荷，你需要按以下规则重组并输出：

1. 顶层键必须按此顺序出现：
   1. `metadata`
   2. `services`
   3. `safety_limits`
   4. `notifications`
2. `metadata` 的键顺序必须为：
   1. `scenario_name`（来自 `fleet_profile.name`）
   2. `locale`（来自 `fleet_profile.locale`）
   3. `owner`（来自 `fleet_profile.owner`）
   4. `revision`（来自 `fleet_profile.revision`）
   5. `generated_by`（固定值：`yaml-task-builder`）
3. `services` 必须是列表，顺序严格跟随 `service_order`。
4. 每个 service 对象的键顺序必须为：
   1. `id`
   2. `enabled`
   3. `rollout`
   4. `endpoints`
5. 每个 `rollout` 对象的键顺序必须为：
   1. `strategy`
   2. `batches`
6. `safety_limits` 必须是映射，键顺序严格跟随 `threshold_order`，对应值来自 `thresholds`。
7. `notifications` 必须是列表，顺序保持与输入一致；每项键顺序为：`channel`、`template`、`recipients`。

格式约束（必须同时满足）：
- 输出必须是可解析 YAML。
- 必须使用块状（block-style）写法，不允许流式集合写法。
- 必须保留上述所有键顺序。
- Unicode 文本必须可读（不能写成 `\uXXXX` 转义序列）。
- 只允许创建这一个输出文件：`/root/outputs/generated_config.yaml`。
