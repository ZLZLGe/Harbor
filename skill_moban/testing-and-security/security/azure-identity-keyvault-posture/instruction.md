# 任务说明（Azure Identity Key Vault Posture）

你需要根据多语言 Azure 身份策略输入表，生成一份稳定、可程序化判定的 posture 报告 CSV。

## 输入
- 输入文件：`/app/workspace/input/azure_access.csv`
- 输入字段顺序固定如下：
  - `app`
  - `language`
  - `credential_type`
  - `uses_managed_identity`
  - `keyvault_ops`
  - `content_safety_enabled`
  - `token_refresh_minutes`

## 输出
- 输出文件：`/app/workspace/output/azure_identity_posture.csv`
- 输出字段必须且仅能按以下顺序写出：
  - `app`
  - `identity_grade`
  - `keyvault_readiness`
  - `rotation_needed`
  - `notes`

## 判定规则
1. `identity_grade`：
   - 当 `uses_managed_identity = yes` 且 `credential_type` 属于 `{DefaultAzureCredential, ManagedIdentityCredential}` 时输出 `A`
   - 当 `uses_managed_identity = yes` 但 `credential_type` 不在上述集合中时输出 `B`
   - 其他情况输出 `C`
2. `keyvault_readiness`：
   - 当 `keyvault_ops` 属于 `{keys, secrets, certificates, multi}` 时输出 `ready`
   - 其他情况输出 `missing`
3. `rotation_needed`：
   - 当 `token_refresh_minutes > 60` 时输出 `yes`
   - 或当 `credential_type` 包含子串 `ClientSecret` 时输出 `yes`
   - 否则输出 `no`
4. `notes`：严格按以下顺序拼接 3 个标签，并使用英文分号 `;` 分隔：
   - 第一段：`uses_managed_identity = yes` 输出 `managed_identity`，否则输出 `explicit_credential`
   - 第二段：`keyvault_readiness = ready` 输出 `kv_ready`，否则输出 `kv_missing`
   - 第三段：`content_safety_enabled = yes` 输出 `content_safety_on`，否则输出 `content_safety_off`

## 排序规则
- 输出必须按 `app` 升序排序。

## 格式与限制
- 所有输出值都必须为稳定文本，不允许依赖随机数、当前时间或其他非确定性信息。
- 不允许输出额外字段。
- 不允许修改输入文件。
- 不允许将空值表示为 `null`、`None`、`nan`、`NaN`。
- 若调用任何外部模型，必须通过环境变量注入密钥，禁止在日志或输出中明文回显密钥。
