#!/usr/bin/env bash
set -euo pipefail

TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export TASK_ROOT

python3 <<'PY'
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/root/data"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/root/output"))
TASK_ROOT = Path(os.environ["TASK_ROOT"]).resolve()
PROFILE = json.loads((DATA_DIR / "engagement" / "target_profile.json").read_text(encoding="utf-8"))
BASE_URL = PROFILE["target_base_url"]
IDENTITIES = {item["label"]: item for item in PROFILE["allowed_identities"]}
SERVICE_SCRIPT_CANDIDATES = [
    Path("/services/orderhub-api/server.py"),
    TASK_ROOT / "environment" / "hidden-service-src" / "server.py",
]
DEFAULT_ACCESS_LOG = Path("/var/log/orderhub-api/access.log")


def ensure_service_running() -> None:
    try:
        request("GET", "/health", None, client="solver-health")
        return
    except Exception:
        pass

    service_script = next((path for path in SERVICE_SCRIPT_CANDIDATES if path.exists()), None)
    if service_script is None:
        raise RuntimeError(f"orderhub service script not found: {SERVICE_SCRIPT_CANDIDATES}")

    access_log = DEFAULT_ACCESS_LOG
    try:
        access_log.parent.mkdir(parents=True, exist_ok=True)
        with access_log.open("a", encoding="utf-8"):
            pass
    except Exception:
        access_log = TASK_ROOT / ".tmp_access.log"

    env = os.environ.copy()
    env["ORDERHUB_PORT"] = "8142"
    env["ORDERHUB_SEED_DIR"] = str(DATA_DIR / "seed")
    env["ORDERHUB_TENANCY_PATH"] = str(DATA_DIR / "tenancy" / "account_map.json")
    env["ORDERHUB_ACCESS_LOG"] = str(access_log)
    log_path = Path("/tmp/orderhub-api.log")
    process = subprocess.Popen(
        [sys.executable, str(service_script)],
        env=env,
        cwd=str(service_script.parent),
        stdout=log_path.open("a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for _ in range(60):
        try:
            request("GET", "/health", None, client="solver-health")
            return
        except Exception:
            time.sleep(0.5)
    process.poll()
    details = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    raise RuntimeError(f"orderhub service failed to start; returncode={process.returncode}; log={details[:2000]}")


def request(method: str, path: str, identity_label: str | None = None, body: dict | None = None, client: str = "official-solver") -> tuple[int, dict, str]:
    url = BASE_URL + path
    headers = {"X-Client": client}
    if identity_label is not None:
        identity = IDENTITIES[identity_label]
        headers[identity["header_name"]] = identity["header_value"]
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, method=method, headers=headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, dict(resp.headers.items()), text
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8")
        return exc.code, dict(exc.headers.items()), text


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


if OUTPUT_DIR.exists():
    shutil.rmtree(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
evidence_dir = OUTPUT_DIR / "evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)

ensure_service_running()

openapi_status, _, openapi_text = request("GET", "/openapi.json", None)
assert openapi_status == 200
openapi_doc = json.loads(openapi_text)

inventory_lines = []
for path_name, methods in sorted(openapi_doc["paths"].items()):
    for method_name in sorted(methods.keys()):
        inventory_lines.append(f"{method_name.upper()} {path_name}")
write_text(evidence_dir / "inventory.txt", "\n".join(inventory_lines) + "\n")

tested_identities = []
for label in ["tenant_alpha_analyst", "tenant_beta_analyst", "support_readonly"]:
    status, _, text = request("GET", "/api/identities/me", label)
    assert status == 200
    payload = json.loads(text)
    tested_identities.append(
        {
            "label": payload["label"],
            "tenant": payload["tenant"],
            "role": payload["role"],
        }
    )

auth_request = "GET /api/orders/10278\nidentity=tenant_alpha_analyst\n"
status, headers, text = request("GET", "/api/orders/10278", "tenant_alpha_analyst")
assert status == 200
write_text(evidence_dir / "authorization-request.txt", auth_request)
write_text(evidence_dir / "authorization-response.json", text + "\n")

export_body = {"scope": "all_tenants", "include_line_items": True, "limit": 6}
export_request = "POST /api/exports/orders\nidentity=support_readonly\nbody=" + json.dumps(export_body, ensure_ascii=False) + "\n"
status, headers, text = request("POST", "/api/exports/orders", "support_readonly", export_body)
assert status == 200
write_text(evidence_dir / "export-request.txt", export_request)
write_text(evidence_dir / "export-response.json", text + "\n")

rate_lines = []
for idx in range(7):
    status, headers, text = request("POST", "/api/exports/orders", "support_readonly", export_body)
    rate_lines.append(
        f"attempt={idx + 1} status={status} limit={headers.get('X-RateLimit-Limit')} remaining={headers.get('X-RateLimit-Remaining')} scope=all_tenants"
    )
write_text(evidence_dir / "rate-limit-sequence.txt", "\n".join(rate_lines) + "\n")

error_request = "GET /api/orders?sort_by=debug_sql\nidentity=tenant_beta_analyst\n"
status, headers, text = request("GET", "/api/orders?sort_by=debug_sql", "tenant_beta_analyst")
assert status == 500
write_text(evidence_dir / "error-request.txt", error_request)
write_text(evidence_dir / "error-response.txt", text + "\n")

findings = [
    {
        "id": "AUTHZ-ORDER-LOOKUP",
        "severity": "high",
        "category": "authorization",
        "endpoint": "GET /api/orders/{order_id}",
        "affected_identity": "tenant_alpha_analyst",
        "summary": "租户 alpha 的分析身份可以直接读取租户 beta 的订单明细。",
        "impact": "订单、联系人和明细可被跨租户读取，隔离边界失效。",
        "recommendation": "在订单明细读取前补齐基于租户和角色的对象级授权检查。",
        "evidence_files": [
            "evidence/authorization-request.txt",
            "evidence/authorization-response.json"
        ]
    },
    {
        "id": "EXPORT-ALL-TENANTS",
        "severity": "high",
        "category": "data-exposure",
        "endpoint": "POST /api/exports/orders",
        "affected_identity": "support_readonly",
        "summary": "只读支持身份可以导出跨租户订单与联系人数据。",
        "impact": "批量导出接口会把多个租户的数据打包返回，扩大泄露面。",
        "recommendation": "为导出接口增加角色约束，并对 all_tenants 范围做显式授权。",
        "evidence_files": [
            "evidence/export-request.txt",
            "evidence/export-response.json"
        ]
    },
    {
        "id": "EXPORT-RATE-LIMIT",
        "severity": "medium",
        "category": "rate-limiting",
        "endpoint": "POST /api/exports/orders",
        "affected_identity": "support_readonly",
        "summary": "导出接口会返回限流头，但连续请求仍可持续成功。",
        "impact": "批量请求可持续占用导出资源，增加数据抓取和资源耗尽风险。",
        "recommendation": "让限流头与实际拦截一致，并在超额后返回阻断状态码。",
        "evidence_files": [
            "evidence/rate-limit-sequence.txt"
        ]
    },
    {
        "id": "ERROR-SQL-DISCLOSURE",
        "severity": "medium",
        "category": "error-handling",
        "endpoint": "GET /api/orders",
        "affected_identity": "tenant_beta_analyst",
        "summary": "非法排序参数会触发回溯和 SQL 片段泄露。",
        "impact": "错误响应会暴露内部实现细节，便于后续定向探测。",
        "recommendation": "对非法参数返回净化后的错误信息，并避免在响应中暴露堆栈与 SQL。",
        "evidence_files": [
            "evidence/error-request.txt",
            "evidence/error-response.txt"
        ]
    }
]

payload = {
    "engagement_id": PROFILE["engagement_id"],
    "target_base_url": BASE_URL,
    "tested_identities": tested_identities,
    "coverage": {
        "endpoint_inventory_count": len(inventory_lines),
        "discovery_complete": True,
        "authn_checked": True,
        "authorization_checked": True,
        "rate_limit_checked": True,
        "error_handling_checked": True
    },
    "findings": findings
}

write_text(OUTPUT_DIR / "security_findings.json", json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

repro = f"""# OrderHub API Security Review

## Scope

- 目标：`{BASE_URL}`
- 身份：`tenant_alpha_analyst`、`tenant_beta_analyst`、`support_readonly`
- 范围：订单列表、订单明细、导出接口、错误处理

## Coverage

| Endpoint | Identity | Observation |
| --- | --- | --- |
| GET /openapi.json | anonymous | 已读取接口合同并整理端点清单 |
| GET /api/identities/me | all allowed identities | 已确认三个允许身份的租户与角色 |
| GET /api/orders/{{order_id}} | tenant_alpha_analyst | 已确认跨租户订单明细可被读取 |
| POST /api/exports/orders | support_readonly | 已确认跨租户导出与限流缺口 |
| GET /api/orders?sort_by=debug_sql | tenant_beta_analyst | 已确认错误响应泄露内部细节 |

## Findings

1. `AUTHZ-ORDER-LOOKUP`
   - 端点：`GET /api/orders/{{order_id}}`
   - 身份：`tenant_alpha_analyst`
   - 观察：alpha 身份读取到 beta 订单 `10278` 的完整明细。
   - 证据：`authorization-request.txt`、`authorization-response.json`
   - 复现：`GET /api/orders/10278`

2. `EXPORT-ALL-TENANTS`
   - 端点：`POST /api/exports/orders`
   - 身份：`support_readonly`
   - 观察：只读支持身份能导出 `all_tenants` 范围，并拿到联系人信息。
   - 证据：`export-request.txt`、`export-response.json`
   - 复现：提交 `{{"scope":"all_tenants","include_line_items":true,"limit":6}}`

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
"""
write_text(OUTPUT_DIR / "reproduction.md", repro)
PY
