from __future__ import annotations

import requests

from common import BROKER_TOKEN, BROKER_URL, DATA_DIR, OUT_DIR, ensure_dirs, read_json, write_json


def main() -> None:
    ensure_dirs()
    bundle = read_json(OUT_DIR.parent / "state" / "base_bundle.json")
    release_id = bundle["release_id"]

    response = requests.get(
        f"{BROKER_URL}/api/v1/provenance",
        headers={"X-Release-Broker-Token": BROKER_TOKEN},
        params={"release_id": release_id},
        timeout=10,
    )
    if response.status_code == 200:
        provenance_payload = response.json()
    else:
        provenance_payload = read_json(DATA_DIR / "fallback_provenance.json")

    records = {
        item["artifact_id"]: item
        for item in provenance_payload.get("records", [])
    }

    for artifact in bundle["artifacts"]:
        record = records.get(artifact["artifact_id"])
        if record:
            artifact["provenance_verified"] = bool(record["verified"])
            artifact["attestation_id"] = record["attestation_id"]

    deployable_artifacts = [item for item in bundle["artifacts"] if item["deployable"]]
    attested_count = sum(1 for item in deployable_artifacts if item["provenance_verified"])

    bundle["source"] = provenance_payload["source"]
    bundle["summary"]["attested_count"] = attested_count
    bundle["summary"]["promotion_ready_count"] = attested_count

    write_json(OUT_DIR / "release-bundle.json", bundle)


if __name__ == "__main__":
    main()
