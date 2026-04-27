#!/bin/bash
set -euo pipefail

cat > /app/workspace/gateway/app.py <<'PY'
from __future__ import annotations

import base64
import csv
import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import requests
from flask import Flask, g, jsonify, request

app = Flask(__name__)

DATA_ROOT = Path("/app/workspace/data")
RATE_SERVICE_URL = os.environ.get("RATE_SERVICE_URL", "http://127.0.0.1:9101")
BOOKING_SERVICE_URL = os.environ.get("BOOKING_SERVICE_URL", "http://127.0.0.1:9102")
TIMEOUT_SECONDS = 1.0

SERVICE_LEVELS = {"standard", "expedited", "overnight"}
SORTS = {"price", "-price", "eta", "-eta"}
LABEL_FORMATS = {"pdf", "zpl"}


def load_partners():
    raw = json.loads((DATA_ROOT / "partners.json").read_text(encoding="utf-8"))
    return {partner["apiKey"]: partner for partner in raw["partners"]}


def load_orders():
    orders = {}
    with (DATA_ROOT / "orders.ndjson").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                order = json.loads(line)
                orders[order["orderId"]] = order
    return orders


def load_postals():
    with (DATA_ROOT / "postal_zones.csv").open(encoding="utf-8") as handle:
        return {row["postal"]: row for row in csv.DictReader(handle)}


PARTNERS_BY_KEY = load_partners()
ORDERS = load_orders()
POSTALS = load_postals()
QUOTE_CACHE = {}
SHIPMENTS = {}
IDEMPOTENCY = {}
RATE_LIMITS = {}


def error_response(status, code, message, details=None, headers=None):
    response = jsonify({"error": {"code": code, "message": message, "details": details or []}})
    response.status_code = status
    if hasattr(g, "rate_headers"):
        for key, value in g.rate_headers.items():
            response.headers[key] = str(value)
    if headers:
        for key, value in headers.items():
            response.headers[key] = str(value)
    return response


def success_response(data, status=200, meta=None, links=None, headers=None):
    response = jsonify({"data": data, "meta": meta or {}, "links": links or {}})
    response.status_code = status
    if hasattr(g, "rate_headers"):
        for key, value in g.rate_headers.items():
            response.headers[key] = str(value)
    if headers:
        for key, value in headers.items():
            response.headers[key] = str(value)
    return response


def auth_partner():
    api_key = request.headers.get("X-Partner-Key")
    if not api_key or api_key not in PARTNERS_BY_KEY:
        return None, error_response(401, "unauthorized", "Missing or invalid API key")
    partner = PARTNERS_BY_KEY[api_key]
    limit_info = partner["rateLimit"]
    now = time.time()
    bucket = RATE_LIMITS.setdefault(partner["id"], [])
    bucket[:] = [ts for ts in bucket if now - ts < limit_info["windowSeconds"]]
    reset_at = int((bucket[0] + limit_info["windowSeconds"]) if bucket else (now + limit_info["windowSeconds"]))
    if len(bucket) >= limit_info["limit"]:
        g.rate_headers = {
            "X-RateLimit-Limit": limit_info["limit"],
            "X-RateLimit-Remaining": 0,
            "X-RateLimit-Reset": reset_at,
        }
        retry_after = max(1, int(limit_info["windowSeconds"] - (now - bucket[0])))
        return None, error_response(
            429,
            "rate_limit_exceeded",
            "Rate limit exceeded",
            headers={"Retry-After": retry_after},
        )
    bucket.append(now)
    g.rate_headers = {
        "X-RateLimit-Limit": limit_info["limit"],
        "X-RateLimit-Remaining": max(0, limit_info["limit"] - len(bucket)),
        "X-RateLimit-Reset": int(bucket[0] + limit_info["windowSeconds"]),
    }
    return partner, None


def parse_positive_int(value, field, details, syntactic=False):
    if value is None:
        details.append({"field": field, "code": "required", "message": f"{field} is required"})
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        if syntactic:
            raise ValueError(field)
        details.append({"field": field, "code": "invalid_integer", "message": f"{field} must be an integer"})
        return None
    if parsed <= 0:
        details.append({"field": field, "code": "must_be_positive", "message": f"{field} must be a positive integer"})
    return parsed


def parse_ship_date(value, details):
    if not value:
        details.append({"field": "shipDate", "code": "required", "message": "shipDate is required"})
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        details.append({"field": "shipDate", "code": "invalid_date", "message": "shipDate must use YYYY-MM-DD"})
        return None


def quote_public_id(rate, origin, destination, weight, ship_date):
    seed = json.dumps(
        {
            "rateId": rate["rateId"],
            "origin": origin,
            "destination": destination,
            "weight": weight,
            "shipDate": ship_date,
        },
        sort_keys=True,
    )
    return "qt_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:18]


def encode_cursor(offset):
    raw = json.dumps({"offset": offset}, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor):
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        offset = int(payload["offset"])
        if offset < 0:
            raise ValueError
        return offset
    except Exception as exc:
        raise ValueError("page[cursor]") from exc


def self_link():
    return request.full_path[:-1] if request.full_path.endswith("?") else request.full_path


def next_link(cursor):
    args = request.args.to_dict(flat=True)
    args["page[cursor]"] = cursor
    return request.path + "?" + urlencode(args)


def call_json(method, url, payload):
    try:
        response = requests.request(method, url, json=payload, timeout=TIMEOUT_SECONDS)
    except requests.Timeout:
        return None, error_response(
            503,
            "downstream_timeout",
            "Downstream service timed out",
            headers={"Retry-After": 2},
        )
    except requests.RequestException:
        return None, error_response(
            503,
            "downstream_unavailable",
            "Downstream service is unavailable",
            headers={"Retry-After": 2},
        )
    if response.status_code >= 500:
        return None, error_response(502, "bad_gateway", "Downstream service returned an error")
    try:
        return response.json(), None
    except ValueError:
        return None, error_response(502, "bad_gateway", "Downstream service returned invalid JSON")


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "shipping-gateway"})


@app.get("/api/v1/shipping-quotes")
def shipping_quotes():
    partner, auth_error = auth_partner()
    if auth_error:
        return auth_error

    details = []
    origin = request.args.get("originPostal")
    destination = request.args.get("destinationPostal")
    for field, value in [("originPostal", origin), ("destinationPostal", destination)]:
        if not value:
            details.append({"field": field, "code": "required", "message": f"{field} is required"})
        elif value not in POSTALS:
            details.append({"field": field, "code": "unknown_postal", "message": f"{field} is not supported"})

    try:
        weight = parse_positive_int(request.args.get("weightGrams"), "weightGrams", details, syntactic=True)
        limit = int(request.args.get("page[limit]", "20"))
    except ValueError as exc:
        return error_response(400, "bad_request", "Query parameter could not be parsed", [{"field": str(exc), "code": "parse_error", "message": "Invalid query syntax"}])

    if limit <= 0:
        details.append({"field": "page[limit]", "code": "must_be_positive", "message": "page[limit] must be positive"})
    if limit > 50:
        details.append({"field": "page[limit]", "code": "too_large", "message": "page[limit] must be at most 50"})

    ship_date_obj = parse_ship_date(request.args.get("shipDate"), details)
    service_level = request.args.get("serviceLevel")
    carrier = request.args.get("carrier")
    sort = request.args.get("sort", "price")

    if service_level and service_level not in SERVICE_LEVELS:
        details.append({"field": "serviceLevel", "code": "unknown_enum", "message": "Unknown serviceLevel"})
    if sort not in SORTS:
        details.append({"field": "sort", "code": "unknown_enum", "message": "Unknown sort"})
    if request.args.get("page[cursor]"):
        try:
            offset = decode_cursor(request.args["page[cursor]"])
        except ValueError:
            return error_response(400, "bad_request", "Query parameter could not be parsed", [{"field": "page[cursor]", "code": "parse_error", "message": "Invalid cursor"}])
    else:
        offset = 0

    if details:
        return error_response(422, "validation_error", "Request validation failed", details)

    if service_level and service_level not in partner["allowedServiceLevels"]:
        return error_response(403, "forbidden", "Partner is not allowed to use the requested service level")
    if carrier and carrier not in partner["allowedCarriers"]:
        return error_response(403, "forbidden", "Partner is not allowed to use the requested carrier")

    upstream_payload = {
        "originPostal": origin,
        "destinationPostal": destination,
        "weightGrams": weight,
        "shipDate": request.args["shipDate"],
    }
    payload, upstream_error = call_json("POST", f"{RATE_SERVICE_URL}/internal/rates", upstream_payload)
    if upstream_error:
        return upstream_error

    quotes = []
    for rate in payload.get("rates", []):
        if not rate.get("available"):
            continue
        if rate["carrier"] not in partner["allowedCarriers"]:
            continue
        if rate["serviceLevel"] not in partner["allowedServiceLevels"]:
            continue
        if service_level and rate["serviceLevel"] != service_level:
            continue
        if carrier and rate["carrier"] != carrier:
            continue
        quote_id = quote_public_id(rate, origin, destination, weight, request.args["shipDate"])
        quote = {
            "quoteId": quote_id,
            "carrier": rate["carrier"],
            "serviceLevel": rate["serviceLevel"],
            "price": {"amount": int(rate["amount"]), "currency": rate["currency"]},
            "eta": {"minDays": int(rate["etaMinDays"]), "maxDays": int(rate["etaMaxDays"])},
            "expiresAt": (ship_date_obj + timedelta(days=1)).isoformat() + "T12:00:00Z",
        }
        QUOTE_CACHE[quote_id] = {**quote, "partnerId": partner["id"], "originPostal": origin, "destinationPostal": destination, "weightGrams": weight}
        quotes.append(quote)

    reverse = sort.startswith("-")
    if sort.lstrip("-") == "price":
        quotes.sort(key=lambda q: (q["price"]["amount"], q["eta"]["maxDays"], q["quoteId"]), reverse=reverse)
    else:
        quotes.sort(key=lambda q: (q["eta"]["maxDays"], q["price"]["amount"], q["quoteId"]), reverse=reverse)

    page = quotes[offset : offset + limit]
    has_more = offset + limit < len(quotes)
    links = {"self": self_link()}
    if has_more:
        links["next"] = next_link(encode_cursor(offset + limit))
    return success_response(page, meta={"count": len(page), "hasMore": has_more}, links=links)


def parse_json_body():
    try:
        body = request.get_json(force=True)
    except Exception:
        return None, error_response(400, "bad_request", "Malformed JSON body")
    if not isinstance(body, dict):
        return None, error_response(422, "validation_error", "Request validation failed", [{"field": "body", "code": "invalid_type", "message": "Body must be a JSON object"}])
    return body, None


@app.post("/api/v1/shipments")
def create_shipment():
    partner, auth_error = auth_partner()
    if auth_error:
        return auth_error
    body, body_error = parse_json_body()
    if body_error:
        return body_error

    idempotency_key = request.headers.get("Idempotency-Key")
    details = []
    if not idempotency_key:
        details.append({"field": "Idempotency-Key", "code": "required", "message": "Idempotency-Key header is required"})
    for field in ["quoteId", "orderId", "labelFormat"]:
        if not body.get(field):
            details.append({"field": field, "code": "required", "message": f"{field} is required"})
    if body.get("labelFormat") and body["labelFormat"] not in LABEL_FORMATS:
        details.append({"field": "labelFormat", "code": "unknown_enum", "message": "Unknown labelFormat"})
    if "metadata" in body and not isinstance(body["metadata"], dict):
        details.append({"field": "metadata", "code": "invalid_type", "message": "metadata must be an object"})

    quote = QUOTE_CACHE.get(body.get("quoteId"))
    if body.get("quoteId") and (not quote or quote["partnerId"] != partner["id"]):
        details.append({"field": "quoteId", "code": "unknown_quote", "message": "quoteId is unknown or expired"})
    order = ORDERS.get(body.get("orderId"))
    if body.get("orderId") and not order:
        details.append({"field": "orderId", "code": "unknown_order", "message": "orderId is unknown"})
    elif order and order["partnerId"] != partner["id"]:
        return error_response(403, "forbidden", "Partner is not allowed to create shipments for this order")

    if details:
        return error_response(422, "validation_error", "Request validation failed", details)

    body_fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    idem_key = (partner["id"], idempotency_key)
    if idem_key in IDEMPOTENCY:
        previous = IDEMPOTENCY[idem_key]
        if previous["fingerprint"] != body_fingerprint:
            return error_response(409, "idempotency_conflict", "Idempotency-Key was reused with a different request body")
        shipment = SHIPMENTS[previous["shipmentId"]]
        return success_response(shipment, status=200, headers={"Location": f"/api/v1/shipments/{shipment['shipmentId']}"})

    booking_payload = {
        "partnerId": partner["id"],
        "orderId": body["orderId"],
        "quote": quote,
        "labelFormat": body["labelFormat"],
        "metadata": body.get("metadata", {}),
    }
    payload, upstream_error = call_json("POST", f"{BOOKING_SERVICE_URL}/internal/bookings", booking_payload)
    if upstream_error:
        return upstream_error

    shipment = {
        "shipmentId": payload["shipmentId"],
        "orderId": body["orderId"],
        "quote": {
            "quoteId": quote["quoteId"],
            "carrier": quote["carrier"],
            "serviceLevel": quote["serviceLevel"],
            "price": quote["price"],
            "eta": quote["eta"],
            "expiresAt": quote["expiresAt"],
        },
        "labelFormat": body["labelFormat"],
        "metadata": body.get("metadata", {}),
        "trackingNumber": payload["trackingNumber"],
        "labelUrl": payload["labelUrl"],
        "partnerId": partner["id"],
    }
    SHIPMENTS[shipment["shipmentId"]] = shipment
    IDEMPOTENCY[idem_key] = {"fingerprint": body_fingerprint, "shipmentId": shipment["shipmentId"]}
    return success_response(shipment, status=201, headers={"Location": f"/api/v1/shipments/{shipment['shipmentId']}"})


@app.get("/api/v1/shipments/<shipment_id>")
def get_shipment(shipment_id):
    partner, auth_error = auth_partner()
    if auth_error:
        return auth_error
    shipment = SHIPMENTS.get(shipment_id)
    if not shipment or shipment["partnerId"] != partner["id"]:
        return error_response(404, "not_found", "Shipment not found")
    return success_response(shipment)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("GATEWAY_PORT", "8080")))
PY

chmod 644 /app/workspace/gateway/app.py
