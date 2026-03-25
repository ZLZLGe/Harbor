def decode_header(data: bytes) -> dict[str, int]:
    text = data.decode("utf-8", errors="ignore").strip()
    if ":" not in text:
        raise ValueError("bad header")
    fmt, size_text = text.split(":", 1)
    if fmt not in {"zip", "tar"}:
        raise ValueError("bad format")
    return {"format": fmt, "size": int(size_text)}
