from __future__ import annotations

from common import STATE_DIR, ensure_dirs, read_json, write_json


def main() -> None:
    ensure_dirs()
    payload = read_json(STATE_DIR / "release_candidates.json")
    artifacts = []
    for item in payload["candidates"]:
        artifacts.append(
            {
                "artifact_id": item["artifact_id"],
                "repo": item["repo"],
                "version": item["version"],
                "git_sha": item["git_sha"],
                "artifact_name": item["artifact_name"],
                "digest": item["digest"],
                "channel": item["channel"],
                "kind": item["kind"],
                "deployable": item["channel"] == "stable",
                "requires_attestation": item["requires_attestation"],
                "promotion_targets": item["promotion_targets"],
                "provenance_verified": False,
                "attestation_id": None,
            }
        )

    bundle = {
        "release_id": payload["release_id"],
        "generated_at": payload["generated_at"],
        "source": payload["source"],
        "artifacts": artifacts,
        "summary": {
            "artifact_count": len(artifacts),
            "deployable_count": sum(1 for item in artifacts if item["deployable"]),
            "attested_count": 0,
            "promotion_ready_count": 0,
        },
    }
    write_json(STATE_DIR / "base_bundle.json", bundle)


if __name__ == "__main__":
    main()
