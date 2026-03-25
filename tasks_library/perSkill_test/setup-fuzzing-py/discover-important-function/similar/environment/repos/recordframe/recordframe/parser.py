def decode_length_prefix(blob: bytes) -> tuple[int, bytes]:
    if len(blob) < 2:
        raise ValueError("blob too short")
    length = int.from_bytes(blob[:2], "big")
    payload = blob[2:]
    if length != len(payload):
        raise ValueError("length mismatch")
    return length, payload


def parse_record_stream(blob: bytes) -> list[dict[str, str]]:
    length, payload = decode_length_prefix(blob)
    if length == 0:
        return []
    text = payload.decode("utf-8")
    records = []
    for line in text.splitlines():
        if not line:
            continue
        if ":" not in line:
            raise ValueError("missing separator")
        key, value = line.split(":", 1)
        records.append({"key": key.strip(), "value": value.strip()})
    return records
