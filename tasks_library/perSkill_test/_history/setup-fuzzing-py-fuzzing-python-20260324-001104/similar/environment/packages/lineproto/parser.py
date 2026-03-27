import base64


def parse_frame(data: bytes) -> dict[str, object]:
    if not data:
        return {"status": "empty"}

    if b"|" not in data:
        return {"status": "raw", "size": len(data)}

    parts = data.split(b"|")
    if len(parts) < 4:
        return {"status": "partial", "parts": len(parts)}

    header = parts[0].decode("ascii", errors="ignore")
    length_text = parts[1].decode("ascii", errors="ignore") or "0"
    try:
        declared_len = int(length_text)
    except ValueError:
        return {"status": "bad-length", "header": header}

    payload = parts[2]
    checksum = parts[3].decode("ascii", errors="ignore")

    if header.startswith("B64:"):
        try:
            payload = base64.b64decode(payload, validate=False)
        except Exception:
            return {"status": "bad-base64", "header": header}

    if declared_len != len(payload):
        return {
            "status": "length-mismatch",
            "header": header,
            "declared_len": declared_len,
            "actual_len": len(payload),
        }

    if checksum == "SUM" and payload:
        checksum_value = sum(payload) % 17
        if checksum_value == 0:
            return {"status": "balanced", "header": header}

    if payload.startswith(b"CMD:"):
        command = payload[4:].decode("utf-8", errors="ignore")
        if command.endswith("!"):
            return {"status": "command", "command": command}

    return {"status": "ok", "header": header, "payload_size": len(payload)}
