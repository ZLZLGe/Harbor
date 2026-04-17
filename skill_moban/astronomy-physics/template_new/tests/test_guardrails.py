import hashlib
import json
import os
from pathlib import Path


DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/app/data"))
SERVICE_PATH = Path(
    os.environ.get("SERVICE_PATH", "/services/observatory-api/server.py")
)
OUTPUT_PATH = Path(os.environ.get("OUTPUT_PATH", "/app/output/catalog_vetting.json"))

EXPECTED_HASHES = {
    "data/target_catalog.json": "c231623ff781e7aa897cf0e90a8386cf9e0cafac130cf72208f569f0eefc7d41",
    "data/targets/TIC-146712781/sector_a.csv": "1ca27efa2b76d8de13ad8a6a9d2d9b58bd2bd1b3772315e1691f901aaab0aa48",
    "data/targets/TIC-220039452/sector_a.csv": "06a9e5d15ed8c410ea96fd245c875812582a6ea5152342f084f44814aafd7b5b",
    "data/targets/TIC-381920550/sector_b.csv": "43535d48a94b49d3fad487f4e5825b3514fa45619b2f57b8800481b2f2337b90",
    "data/targets/TIC-440119211/sector_c.csv": "557c2c706f233341e677525340f694ca53d312f53af7a873565234f41991bb91",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_raw_inputs_and_hidden_service_script_is_unchanged():
    file_map = {
        "data/target_catalog.json": DATA_ROOT / "target_catalog.json",
        "data/targets/TIC-146712781/sector_a.csv": DATA_ROOT / "targets/TIC-146712781/sector_a.csv",
        "data/targets/TIC-220039452/sector_a.csv": DATA_ROOT / "targets/TIC-220039452/sector_a.csv",
        "data/targets/TIC-381920550/sector_b.csv": DATA_ROOT / "targets/TIC-381920550/sector_b.csv",
        "data/targets/TIC-440119211/sector_c.csv": DATA_ROOT / "targets/TIC-440119211/sector_c.csv",
    }
    for name, path in file_map.items():
        assert path.exists(), f"Missing protected file: {name}"
        assert _sha256(path) == EXPECTED_HASHES[name], f"Protected file changed: {name}"
    recorded_hash = Path("/opt/observatory-server.sha256")
    assert recorded_hash.exists(), "Missing hidden service checksum record"
    assert _sha256(SERVICE_PATH) == recorded_hash.read_text(encoding="utf-8").strip()


def test_bundle_is_not_placeholder_text():
    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    entries = payload["entries"]
    assert len(entries) >= 4
    for entry in entries:
        assert entry["verdict"] in {"planet_candidate", "eclipsing_binary"}
        assert len(entry["verdict_reason"].strip()) >= 40
        assert entry["verdict_reason"].strip().lower() not in {
            "todo",
            "placeholder",
            "n/a",
            "unknown",
        }
