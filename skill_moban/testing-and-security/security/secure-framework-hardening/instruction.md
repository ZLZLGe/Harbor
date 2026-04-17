# 任务说明（Secure Framework Hardening）

你需要根据服务级安全控制项输入，生成稳定、可程序化校验的加固计划 CSV。

## 输入
- 输入文件：`workspace/input/security_controls.csv`
- 字段顺序固定为：
  - `service`
  - `framework`
  - `auth_enabled`
  - `input_validation`
  - `csrf_protection`
  - `rate_limit`
  - `secrets_vault`
- 控制项字段取值为 `yes` 或 `no`。

## 输出
- 主输出文件：`/app/workspace/output/hardening_plan.csv`
- 输出字段必须且仅能按以下顺序出现：
  - `service`
  - `risk_score`
  - `priority`
  - `missing_controls`

## 处理规则
1. 每条输入记录生成一条输出记录，不允许丢行。
2. 按以下固定顺序检查缺失控制项：`auth_enabled,input_validation,csrf_protection,rate_limit,secrets_vault`。
3. 对于值为 `no` 的控制项，将其加入 `missing_controls`。
4. `risk_score = 缺失项个数 * 20`，结果为整数，不保留小数。
5. `priority` 规则：
   - `risk_score >= 60` 输出 `critical`
   - `risk_score >= 40` 且 `< 60` 输出 `high`
   - `risk_score >= 20` 且 `< 40` 输出 `medium`
   - 其他情况输出 `low`
6. `missing_controls` 在没有缺失项时写 `none`；否则按固定顺序用 `;` 连接。
7. 排序规则：先按 `risk_score` 降序，再按 `service` 升序。
8. 空值规则：若某个输出字段无法计算，写空字符串；禁止输出 `null`、`None`、`nan`。

## 禁止事项
- 不允许修改输入文件。
- 不允许改变输出字段名、字段顺序或主输出路径。
- 不允许写入依赖联网、随机数或主观判断的逻辑。
- 不允许输出额外主结果文件替代 `hardening_plan.csv`。
