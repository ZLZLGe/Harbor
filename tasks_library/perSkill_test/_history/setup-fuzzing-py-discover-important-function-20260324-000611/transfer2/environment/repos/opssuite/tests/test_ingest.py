from opssuite.ingest.batch_loader import load_batch_manifest
from opssuite.ingest.http_payload import parse_ingest_request


def test_parse_ingest_request():
    payload = parse_ingest_request(b'{"batch_id": "A-17", "items": 2}')
    assert payload["batch_id"] == "A-17"


def test_load_batch_manifest():
    rows = load_batch_manifest('{"batch_id": "A-17"}\n{"batch_id": "A-18"}\n')
    assert len(rows) == 2
