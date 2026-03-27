import json
import zlib


def load_manifest(blob: bytes) -> dict[str, object]:
    if not blob:
        return {"status": "empty"}

    try:
        raw = zlib.decompress(blob)
    except zlib.error:
        return {"status": "bad-compression"}

    try:
        document = json.loads(raw.decode("utf-8"))
    except Exception:
        return {"status": "bad-json"}

    route = document.get("route", "")
    metadata = document.get("metadata", {})
    if route.startswith("/admin/") and metadata.get("owner") == "ops":
        return {"status": "privileged", "route": route}
    if document.get("retries", 0) > 4 and metadata.get("critical") is True:
        return {"status": "retry-heavy", "route": route}
    return {"status": "ok", "keys": sorted(document.keys())}
