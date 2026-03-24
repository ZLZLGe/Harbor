from __future__ import annotations


def normalize_timestamp(value: str) -> tuple[int, int]:
    whole, dot, fraction = value.partition(".")
    seconds = int(whole)
    if not dot:
        return seconds, 0

    fraction = (fraction + "000000000")[:9]
    return seconds, int(fraction)


def parse_extended_headers(data: bytes) -> dict[str, str]:
    headers: dict[str, str] = {}
    offset = 0

    while offset < len(data):
        length_end = data.find(b" ", offset)
        if length_end == -1:
            raise ValueError("missing record length separator")

        record_length = int(data[offset:length_end])
        record = data[offset : offset + record_length]
        if len(record) != record_length:
            raise ValueError("truncated extended header record")
        if not record.endswith(b"\n"):
            raise ValueError("extended header record must end with newline")

        payload = record[length_end - offset + 1 : -1]
        key, value = payload.split(b"=", 1)
        headers[key.decode("utf-8")] = value.decode("utf-8")
        offset += record_length

    return headers
