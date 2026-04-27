from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

LEDGER_PATH = Path("/tmp/shipping-api/booking-ledger.jsonl")
MODE_PATH = Path("/tmp/shipping-api/booking-mode.txt")


def current_mode() -> str:
    if MODE_PATH.exists():
        return MODE_PATH.read_text(encoding="utf-8").strip() or "normal"
    return "normal"


def append_ledger(payload: dict) -> int:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if LEDGER_PATH.exists():
        existing = [line for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"ts": time.time(), "payload": payload}, sort_keys=True) + "\n")
    return len(existing) + 1


@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "shipment-booking"})


@app.post("/internal/bookings")
def bookings():
    mode = current_mode()
    if mode == "timeout":
        time.sleep(3.0)
    if mode == "invalid":
        return "{not-json", 200, {"Content-Type": "application/json"}
    if mode == "error":
        return jsonify({"error": "temporary booking failure"}), 503

    payload = request.get_json(force=True, silent=False)
    sequence = append_ledger(payload)
    quote = payload.get("quote", {})
    seed = json.dumps(
        {
            "seq": sequence,
            "partnerId": payload.get("partnerId"),
            "orderId": payload.get("orderId"),
            "quoteId": quote.get("quoteId"),
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    shipment_id = "shp_" + digest[:16]
    return jsonify(
        {
            "shipmentId": shipment_id,
            "trackingNumber": "TRK" + digest[16:28].upper(),
            "labelUrl": f"https://labels.local/{shipment_id}.{payload.get('labelFormat', 'pdf')}",
        }
    )


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
    app.run(host="127.0.0.1", port=9102, threaded=True)
