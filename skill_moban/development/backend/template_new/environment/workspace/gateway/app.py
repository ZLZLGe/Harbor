from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

DATA_ROOT = Path("/app/workspace/data")
RATE_SERVICE_URL = os.environ.get("RATE_SERVICE_URL", "http://127.0.0.1:9101")
BOOKING_SERVICE_URL = os.environ.get("BOOKING_SERVICE_URL", "http://127.0.0.1:9102")


def load_partners():
    raw = json.loads((DATA_ROOT / "partners.json").read_text(encoding="utf-8"))
    return {partner["apiKey"]: partner for partner in raw["partners"]}


PARTNERS_BY_KEY = load_partners()
QUOTE_CACHE = {}
SHIPMENTS = {}
IDEMPOTENCY = {}


def error(status, code, message, details=None):
    return jsonify({"error": {"code": code, "message": message, "details": details or []}}), status


def current_partner():
    api_key = request.headers.get("X-Partner-Key")
    if not api_key or api_key not in PARTNERS_BY_KEY:
        return None
    return PARTNERS_BY_KEY[api_key]


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "shipping-gateway"})


@app.get("/api/v1/shipping-quotes")
def shipping_quotes():
    partner = current_partner()
    if not partner:
        return error(401, "unauthorized", "Missing or invalid API key")

    # This intentionally implements only the rough happy path. Complete the
    # public API contract described in /app/workspace/instruction.md.
    try:
        weight = int(request.args.get("weightGrams", "0"))
    except ValueError:
        return error(400, "bad_request", "weightGrams could not be parsed")

    upstream = requests.post(
        f"{RATE_SERVICE_URL}/internal/rates",
        json={
            "originPostal": request.args.get("originPostal"),
            "destinationPostal": request.args.get("destinationPostal"),
            "weightGrams": weight,
            "shipDate": request.args.get("shipDate"),
        },
        timeout=2,
    )
    rates = upstream.json().get("rates", [])
    data = []
    for rate in rates:
        if not rate.get("available"):
            continue
        quote = {
            "quoteId": "qt_" + rate["rateId"].removeprefix("rate_"),
            "carrier": rate["carrier"],
            "serviceLevel": rate["serviceLevel"],
            "price": {"amount": rate["amount"], "currency": rate["currency"]},
            "eta": {"minDays": rate["etaMinDays"], "maxDays": rate["etaMaxDays"]},
            "expiresAt": request.args.get("shipDate", "2026-05-04") + "T12:00:00Z",
        }
        QUOTE_CACHE[quote["quoteId"]] = quote
        data.append(quote)
    return jsonify({"data": data, "meta": {"count": len(data)}, "links": {}})


@app.post("/api/v1/shipments")
def create_shipment():
    partner = current_partner()
    if not partner:
        return error(401, "unauthorized", "Missing or invalid API key")
    body = request.get_json(force=True)
    quote = QUOTE_CACHE.get(body.get("quoteId"))
    if not quote:
        return error(422, "validation_error", "Unknown quoteId")
    upstream = requests.post(
        f"{BOOKING_SERVICE_URL}/internal/bookings",
        json={
            "partnerId": partner["id"],
            "orderId": body.get("orderId"),
            "quote": quote,
            "labelFormat": body.get("labelFormat"),
            "metadata": body.get("metadata", {}),
        },
        timeout=2,
    )
    payload = upstream.json()
    shipment = {
        "shipmentId": payload["shipmentId"],
        "orderId": body.get("orderId"),
        "quote": quote,
        "labelFormat": body.get("labelFormat"),
        "metadata": body.get("metadata", {}),
        "trackingNumber": payload["trackingNumber"],
        "labelUrl": payload["labelUrl"],
        "partnerId": partner["id"],
    }
    SHIPMENTS[shipment["shipmentId"]] = shipment
    return jsonify({"data": shipment, "meta": {}, "links": {}}), 201


@app.get("/api/v1/shipments/<shipment_id>")
def get_shipment(shipment_id):
    partner = current_partner()
    if not partner:
        return error(401, "unauthorized", "Missing or invalid API key")
    shipment = SHIPMENTS.get(shipment_id)
    if not shipment:
        return error(404, "not_found", "Shipment not found")
    return jsonify({"data": shipment, "meta": {}, "links": {}})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("GATEWAY_PORT", "8080")))
