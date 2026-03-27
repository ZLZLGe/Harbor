import base64
import json

from opssuite.auth.token_file import decode_token_blob


def test_decode_token_blob():
    blob = base64.b64encode(json.dumps({"sub": "agent-7"}).encode("utf-8")).decode("utf-8")
    claims = decode_token_blob(blob)
    assert claims["sub"] == "agent-7"
