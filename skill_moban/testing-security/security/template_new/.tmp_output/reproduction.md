# OrderHub API Security Review

## Scope

- 目标：`http://127.0.0.1:8142`
- 身份：`tenant_alpha_analyst`、`tenant_beta_analyst`、`support_readonly`
- 范围：订单列表、订单明细、导出接口、错误处理

## Coverage

| Endpoint | Identity | Observation |
| --- | --- | --- |
| GET /openapi.json | anonymous | 已读取接口合同并整理端点清单 |
| GET /api/identities/me | all allowed identities | 已确认三个允许身份的租户与角色 |
| GET /api/orders/{order_id} | tenant_alpha_analyst | 已确认跨租户订单明细可被读取 |
| POST /api/exports/orders | support_readonly | 已确认跨租户导出与限流缺口 |
| GET /api/orders?sort_by=debug_sql | tenant_beta_analyst | 已确认错误响应泄露内部细节 |

## Findings

1. `AUTHZ-ORDER-LOOKUP`
   - 端点：`GET /api/orders/{order_id}`
   - 身份：`tenant_alpha_analyst`
   - 观察：alpha 身份读取到 beta 订单 `10278` 的完整明细。
   - 证据：`authorization-request.txt`、`authorization-response.json`
   - 复现：`GET /api/orders/10278`

2. `EXPORT-ALL-TENANTS`
   - 端点：`POST /api/exports/orders`
   - 身份：`support_readonly`
   - 观察：只读支持身份能导出 `all_tenants` 范围，并拿到联系人信息。
   - 证据：`export-request.txt`、`export-response.json`
   - 复现：提交 `{"scope":"all_tenants","include_line_items":true,"limit":6}`

3. `EXPORT-RATE-LIMIT`
   - 端点：`POST /api/exports/orders`
   - 身份：`support_readonly`
   - 观察：连续 7 次请求都成功，限流头递减后仍未阻断。
   - 证据：`rate-limit-sequence.txt`
   - 复现：对同一导出体连续发起多次 POST

4. `ERROR-SQL-DISCLOSURE`
   - 端点：`GET /api/orders`
   - 身份：`tenant_beta_analyst`
   - 观察：非法排序参数返回回溯和 SQL 片段。
   - 证据：`error-request.txt`、`error-response.txt`
   - 复现：`GET /api/orders?sort_by=debug_sql`

## Reproduction Steps

1. 读取 `target_profile.json`，按允许身份准备 `X-API-Key`。
2. 读取 `openapi.json`，确认公开端点与参数。
3. 用 `tenant_alpha_analyst` 请求 `GET /api/orders/10278`，保留响应。
4. 用 `support_readonly` 调用 `POST /api/exports/orders`，范围设为 `all_tenants`，保留响应。
5. 对同一导出接口连续发送多次请求，记录状态码和限流头。
6. 用 `tenant_beta_analyst` 访问 `GET /api/orders?sort_by=debug_sql`，保留错误响应。

## Suggested Follow-up

- 在订单明细和导出范围上补齐对象级授权。
- 让导出接口的角色边界和批量范围控制更清晰。
- 把限流头和阻断行为对齐。
- 用净化后的错误响应替换回溯与 SQL 暴露。
