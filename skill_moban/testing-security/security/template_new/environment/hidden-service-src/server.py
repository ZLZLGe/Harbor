from __future__ import annotations

import csv
import json
import os
import threading
import traceback
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PORT = int(os.environ.get("ORDERHUB_PORT", "8142"))
SEED_DIR = Path(os.environ.get("ORDERHUB_SEED_DIR", "/root/data/seed"))
TENANCY_PATH = Path(os.environ.get("ORDERHUB_TENANCY_PATH", "/root/data/tenancy/account_map.json"))
ACCESS_LOG = Path(os.environ.get("ORDERHUB_ACCESS_LOG", "/var/log/orderhub-api/access.log"))

EXPORT_LIMIT = 5
EXPORT_COUNTERS: dict[str, int] = {}
EXPORT_LOCK = threading.Lock()


def load_json(path: Path) -> list[dict] | dict:
    return json.loads(path.read_text(encoding="utf-8"))


CUSTOMERS = load_json(SEED_DIR / "customers.json")
ORDERS = load_json(SEED_DIR / "orders.json")
PRODUCTS = load_json(SEED_DIR / "products.json")
EMPLOYEES = load_json(SEED_DIR / "employees.json")
SHIPPERS = load_json(SEED_DIR / "shippers.json")
TENANCY = load_json(TENANCY_PATH)

with (SEED_DIR / "order_details.csv").open(newline="", encoding="utf-8") as fh:
    ORDER_DETAILS = list(csv.DictReader(fh))

CUSTOMER_BY_ID = {row["customer_id"]: row for row in CUSTOMERS}
ORDER_BY_ID = {row["order_id"]: row for row in ORDERS}
PRODUCT_BY_ID = {row["product_id"]: row for row in PRODUCTS}
EMPLOYEE_BY_ID = {row["employee_id"]: row for row in EMPLOYEES}
SHIPPER_BY_ID = {row["shipper_id"]: row for row in SHIPPERS}
DETAILS_BY_ORDER: dict[str, list[dict]] = {}
for row in ORDER_DETAILS:
    DETAILS_BY_ORDER.setdefault(row["order_id"], []).append(row)

IDENTITY_BY_KEY = {}
for identity in TENANCY["identities"]:
    IDENTITY_BY_KEY[identity["api_key"]] = identity

TENANT_CUSTOMERS = {}
for tenant in TENANCY["tenants"]:
    TENANT_CUSTOMERS[tenant["tenant_id"]] = set(tenant["customer_ids"])


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_openapi_doc() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {"title": "OrderHub Public API", "version": "2026-05"},
        "servers": [{"url": f"http://127.0.0.1:{PORT}"}],
        "paths": {
            "/health": {"get": {"summary": "Service health"}},
            "/openapi.json": {"get": {"summary": "Machine-readable contract"}},
            "/api/identities/me": {"get": {"summary": "Caller identity summary"}},
            "/api/orders": {
                "get": {
                    "summary": "Paginated order summaries",
                    "parameters": [
                        {"name": "limit", "in": "query"},
                        {"name": "cursor", "in": "query"},
                        {"name": "status", "in": "query"},
                        {"name": "sort_by", "in": "query"}
                    ]
                }
            },
            "/api/orders/{order_id}": {"get": {"summary": "Order detail by order ID"}},
            "/api/exports/orders": {"post": {"summary": "Create an order export preview"}}
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
            }
        }
    }


OPENAPI_DOC = build_openapi_doc()


def order_visible_to_identity(order: dict, identity: dict) -> bool:
    if identity["role"] == "support_readonly":
        return True
    return order["customer_id"] in TENANT_CUSTOMERS[identity["tenant"]]


def order_summary(order: dict) -> dict:
    customer = CUSTOMER_BY_ID[order["customer_id"]]
    return {
        "order_id": order["order_id"],
        "customer_id": order["customer_id"],
        "customer_company": customer["company_name"],
        "ship_country": order["ship_country"],
        "ship_city": order["ship_city"],
        "status": order["status"],
        "freight": order["freight"],
        "order_total": order["order_total"]
    }


def order_detail(order: dict) -> dict:
    customer = CUSTOMER_BY_ID[order["customer_id"]]
    employee = EMPLOYEE_BY_ID.get(order["employee_id"], {})
    shipper = SHIPPER_BY_ID.get(order["ship_via"], {})
    line_items = []
    for row in DETAILS_BY_ORDER[order["order_id"]]:
        product = PRODUCT_BY_ID[row["product_id"]]
        unit_price = float(row["unit_price"])
        quantity = int(row["quantity"])
        discount = float(row["discount"])
        line_total = round(unit_price * quantity * (1 - discount), 2)
        line_items.append(
            {
                "product_id": row["product_id"],
                "product_name": product["product_name"],
                "quantity": quantity,
                "unit_price": unit_price,
                "discount": discount,
                "line_total": line_total
            }
        )
    return {
        "order": order,
        "customer": customer,
        "employee": employee,
        "shipper": shipper,
        "line_items": line_items
    }


def export_rows(identity: dict, scope: str, include_line_items: bool, limit: int) -> list[dict]:
    if scope == "tenant" and identity["tenant"] in {"alpha", "beta"}:
        visible_orders = [o for o in ORDERS if o["customer_id"] in TENANT_CUSTOMERS[identity["tenant"]]]
    else:
        visible_orders = list(ORDERS)
    rows = []
    for order in visible_orders[:limit]:
        base = {
            "order_id": order["order_id"],
            "tenant_id": order["tenant_id"],
            "customer_id": order["customer_id"],
            "customer_company": CUSTOMER_BY_ID[order["customer_id"]]["company_name"],
            "contact_name": CUSTOMER_BY_ID[order["customer_id"]]["contact_name"],
            "ship_country": order["ship_country"],
            "status": order["status"],
            "order_total": order["order_total"]
        }
        if include_line_items:
            base["line_items"] = order_detail(order)["line_items"]
        rows.append(base)
    return rows


class OrderHubHandler(BaseHTTPRequestHandler):
    server_version = "OrderHub/2026.05"

    def log_message(self, format: str, *args) -> None:
        return

    def _identity(self) -> dict | None:
        key = self.headers.get("X-API-Key", "")
        return IDENTITY_BY_KEY.get(key)

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw:
            return {}
        return json.loads(raw)

    def _write_json(self, status: int, payload: dict, identity: dict | None, body: dict | None = None, extra_headers: dict | None = None) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(encoded)
        self._log_event(status, identity, body, payload)

    def _write_text(self, status: int, text: str, identity: dict | None, body: dict | None = None, extra_headers: dict | None = None) -> None:
        encoded = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(encoded)
        self._log_event(status, identity, body, text)

    def _log_event(self, status: int, identity: dict | None, body: dict | None, response_preview: dict | str) -> None:
        ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        record = {
            "ts": utc_now(),
            "method": self.command,
            "path": parsed.path,
            "query": {key: values[0] if len(values) == 1 else values for key, values in query.items()},
            "status": status,
            "identity_label": identity["label"] if identity else None,
            "tenant": identity["tenant"] if identity else None,
            "role": identity["role"] if identity else None,
            "client": self.headers.get("X-Client", ""),
            "body": body or {},
            "response_preview": response_preview if isinstance(response_preview, str) else json.dumps(response_preview, ensure_ascii=False)[:400]
        }
        with ACCESS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _require_identity(self) -> dict | None:
        identity = self._identity()
        if identity is None:
            self._write_json(401, {"error": "invalid_api_key"}, None)
            return None
        return identity

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            self._write_json(200, {"ok": True, "service": "orderhub-api", "time": utc_now()}, None)
            return

        if path == "/openapi.json":
            self._write_json(200, OPENAPI_DOC, None)
            return

        identity = self._require_identity()
        if identity is None:
            return

        if path == "/api/identities/me":
            self._write_json(
                200,
                {
                    "label": identity["label"],
                    "tenant": identity["tenant"],
                    "role": identity["role"]
                },
                identity
            )
            return

        if path == "/api/orders":
            try:
                limit = min(max(int(query.get("limit", ["2"])[0]), 1), 10)
                cursor = max(int(query.get("cursor", ["0"])[0]), 0)
                status = query.get("status", [None])[0]
                sort_by = query.get("sort_by", [None])[0]
                allowed_sorts = {"order_date", "freight", "ship_country"}
                if sort_by and sort_by not in allowed_sorts:
                    raise RuntimeError(
                        f"Unhandled sort key: {sort_by}\nSQL: SELECT order_id, ship_country FROM orders ORDER BY {sort_by}"
                    )

                visible = [order for order in ORDERS if order_visible_to_identity(order, identity)]
                if status:
                    visible = [order for order in visible if order["status"] == status]
                if sort_by == "freight":
                    visible.sort(key=lambda item: float(item["freight"]))
                elif sort_by == "ship_country":
                    visible.sort(key=lambda item: item["ship_country"])
                else:
                    visible.sort(key=lambda item: item["order_date"])

                page = visible[cursor: cursor + limit]
                next_cursor = cursor + limit if cursor + limit < len(visible) else None
                payload = {
                    "items": [order_summary(order) for order in page],
                    "page_info": {"next_cursor": next_cursor},
                    "total_visible_orders": len(visible)
                }
                self._write_json(200, payload, identity)
                return
            except Exception:
                self._write_text(500, traceback.format_exc(), identity)
                return

        if path.startswith("/api/orders/"):
            order_id = path.rsplit("/", 1)[-1]
            order = ORDER_BY_ID.get(order_id)
            if order is None:
                self._write_json(404, {"error": "unknown_order"}, identity)
                return
            self._write_json(200, order_detail(order), identity)
            return

        self._write_json(404, {"error": "unknown_route"}, identity)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        identity = self._require_identity()
        if identity is None:
            return
        body = self._json_body()

        if path == "/api/exports/orders":
            scope = body.get("scope", "tenant")
            include_line_items = bool(body.get("include_line_items", False))
            limit = min(max(int(body.get("limit", 8)), 1), 8)
            rows = export_rows(identity, scope, include_line_items, limit)
            with EXPORT_LOCK:
                EXPORT_COUNTERS[identity["label"]] = EXPORT_COUNTERS.get(identity["label"], 0) + 1
                count = EXPORT_COUNTERS[identity["label"]]
            headers = {
                "X-RateLimit-Limit": str(EXPORT_LIMIT),
                "X-RateLimit-Remaining": str(EXPORT_LIMIT - count),
                "X-RateLimit-Reset": "60"
            }
            payload = {
                "job_id": f"exp-{identity['label']}-{count:03d}",
                "requested_by": identity["label"],
                "scope": scope,
                "record_count": len(rows),
                "tenants_included": sorted({row["tenant_id"] for row in rows}),
                "records_sample": rows[: min(3, len(rows))]
            }
            self._write_json(200, payload, identity, body=body, extra_headers=headers)
            return

        self._write_json(404, {"error": "unknown_route"}, identity, body=body)


def main() -> None:
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), OrderHubHandler)
    print(f"orderhub-api listening on {PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
