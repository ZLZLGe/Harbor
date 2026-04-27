from __future__ import annotations

import csv
import hashlib
import json
import time
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

DATA_ROOT = Path("/app/workspace/data")
LEDGER_PATH = Path("/tmp/shipping-api/rate-ledger.jsonl")
MODE_PATH = Path("/tmp/shipping-api/rate-mode.txt")

ZONE_INDEX = {
    row["postal"]: row
    for row in csv.DictReader((DATA_ROOT / "postal_zones.csv").open(encoding="utf-8"))
}

ZONE_RANK = {
    "WEST": 1,
    "NORTHWEST": 2,
    "SOUTHWEST": 3,
    "MIDWEST": 4,
    "SOUTH": 5,
    "EAST": 6,
    "ALASKA": 8,
    "PACIFIC": 9,
}

CARRIER_SERVICES = [
    {"carrier": "roadline", "serviceLevel": "standard", "base": 760, "perKg": 180, "min": 3, "max": 6, "maxWeight": 30000},
    {"carrier": "roadline", "serviceLevel": "expedited", "base": 1240, "perKg": 260, "min": 2, "max": 3, "maxWeight": 18000},
    {"carrier": "skybridge", "serviceLevel": "expedited", "base": 1780, "perKg": 420, "min": 1, "max": 2, "maxWeight": 7000},
    {"carrier": "skybridge", "serviceLevel": "overnight", "base": 3190, "perKg": 650, "min": 1, "max": 1, "maxWeight": 3500},
    {"carrier": "coldchain", "serviceLevel": "standard", "base": 2140, "perKg": 390, "min": 4, "max": 7, "maxWeight": 12000},
]


def current_mode() -> str:
    if MODE_PATH.exists():
        return MODE_PATH.read_text(encoding="utf-8").strip() or "normal"
    return "normal"


def append_ledger(payload: dict) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"ts": time.time(), "payload": payload}, sort_keys=True) + "\n")


def quote_id(seed: str) -> str:
    return "rate_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:18]


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "carrier-rate"})


@app.post("/internal/rates")
def rates():
    mode = current_mode()
    if mode == "timeout":
        time.sleep(3.0)
    if mode == "invalid":
        return "{not-json", 200, {"Content-Type": "application/json"}
    if mode == "error":
        return jsonify({"error": "temporary upstream failure"}), 503

    payload = request.get_json(force=True, silent=False)
    append_ledger(payload)

    origin = ZONE_INDEX.get(str(payload.get("originPostal", "")))
    destination = ZONE_INDEX.get(str(payload.get("destinationPostal", "")))
    weight = int(payload.get("weightGrams", 0))
    ship_date = str(payload.get("shipDate", ""))

    if not origin or not destination:
        return jsonify({"rates": []})

    zone_distance = abs(ZONE_RANK[origin["zone"]] - ZONE_RANK[destination["zone"]])
    remote_surcharge = 950 if destination["remote"] == "true" or origin["remote"] == "true" else 0
    rates = []

    for service in CARRIER_SERVICES:
        available = weight <= service["maxWeight"]
        if service["carrier"] == "coldchain" and destination["zone"] in {"ALASKA", "PACIFIC"}:
            available = False
        amount = service["base"] + int((weight / 1000.0) * service["perKg"]) + zone_distance * 95 + remote_surcharge
        seed = "|".join(
            [
                str(payload.get("originPostal")),
                str(payload.get("destinationPostal")),
                str(weight),
                ship_date,
                service["carrier"],
                service["serviceLevel"],
            ]
        )
        rates.append(
            {
                "rateId": quote_id(seed),
                "carrier": service["carrier"],
                "serviceLevel": service["serviceLevel"],
                "amount": amount,
                "currency": "USD",
                "etaMinDays": service["min"] + min(zone_distance // 3, 2),
                "etaMaxDays": service["max"] + min(zone_distance // 3, 2),
                "available": available,
            }
        )
    return jsonify({"rates": rates})


@app.get("/internal/test/ledger")
def get_ledger():
    if not LEDGER_PATH.exists():
        return jsonify({"calls": []})
    calls = [json.loads(line) for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return jsonify({"calls": calls})


@app.post("/internal/test/reset")
def reset():
    LEDGER_PATH.unlink(missing_ok=True)
    MODE_PATH.write_text("normal", encoding="utf-8")
    return jsonify({"ok": True})


@app.post("/internal/test/mode")
def set_mode():
    payload = request.get_json(force=True, silent=False)
    mode = payload.get("mode", "normal")
    if mode not in {"normal", "timeout", "invalid", "error"}:
        return jsonify({"error": "bad mode"}), 422
    MODE_PATH.write_text(mode, encoding="utf-8")
    return jsonify({"mode": mode})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9101, threaded=True)
