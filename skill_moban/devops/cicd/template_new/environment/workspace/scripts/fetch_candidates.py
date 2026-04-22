from __future__ import annotations

from common import STATE_DIR, broker_get, ensure_dirs, write_json


def main() -> None:
    ensure_dirs()
    payload = broker_get("/api/v1/release-candidates")
    write_json(STATE_DIR / "release_candidates.json", payload)


if __name__ == "__main__":
    main()
