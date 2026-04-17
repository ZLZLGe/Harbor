# 任务说明（DevSecOps Remediation Queue）

你需要读取多源安全 finding 数据，生成去重后的修复队列 CSV。

## 输入
- 输入文件：`/app/workspace/input/findings.jsonl`
- 输入为 JSON Lines 格式，每行一个 JSON 对象。
- 每条记录包含以下字段：
  - `scanner`
  - `id`
  - `severity`
  - `cve`
  - `fix_version`

## 输出
- 主输出文件：`/app/workspace/output/remediation_queue.csv`
- 输出字段必须且仅能按以下顺序写出：
  - `finding_key`
  - `severity`
  - `scanner`
  - `owner_team`
  - `sla_days`
  - `fix_version`

## 处理规则
1. `finding_key` 规则：若 `cve` 非空，则使用 `cve`；否则使用 `id`。
2. 去重规则：同一 `finding_key` 只保留 1 条记录。
3. 去重优先级：
   - 优先保留更高 `severity` 的记录。
   - `severity` 等级固定为：`critical > high > medium > low`。
   - 若 `severity` 相同，则保留 `scanner` 字典序更小的记录。
4. `owner_team` 规则：
   - `scanner = sast` 或 `deps` 时输出 `appsec`
   - `scanner = api` 时输出 `backend`
   - `scanner = pentest` 时输出 `cloudsec`
   - 其他值输出 `platform`
5. `sla_days` 规则：
   - `critical = 3`
   - `high = 7`
   - `medium = 30`
   - `low = 90`
6. `fix_version` 原样输出；若输入为空或 `null`，输出空字符串。

## 排序规则
1. 按 `severity` 从高到低排序。
2. 若 `severity` 相同，再按 `finding_key` 升序排序。

## 格式与约束
- 输出必须是标准 CSV。
- 所有空值必须输出为空字符串。
- 不得输出 `null`、`None`、`nan`、`NaN`。
- 不得增加、删除、重命名或重排输出字段。
- 不得修改输入文件。
- 不得依赖联网、随机数、当前时间或人工交互。
- 如需外部模型调用，必须通过环境变量读取密钥，且不得回显任何 key；本题推荐纯本地实现。
