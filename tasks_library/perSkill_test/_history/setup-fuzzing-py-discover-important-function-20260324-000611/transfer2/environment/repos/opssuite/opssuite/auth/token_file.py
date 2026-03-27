import base64
import json


def decode_token_blob(raw: str) -> dict[str, object]:
    """Decode a base64-encoded token blob into a JSON claims object."""
    data = base64.b64decode(raw.encode("utf-8"))
    return json.loads(data.decode("utf-8"))


def claim_subject(claims: dict[str, object]) -> str:
    return str(claims["sub"])
