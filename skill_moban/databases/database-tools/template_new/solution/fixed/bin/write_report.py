#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


WORKSPACE = Path("/app/workspace")
OUTPUT_PATH = WORKSPACE / "output" / "migration_report.json"

PGHOST = os.environ.get("PGHOST", "/tmp/database-tools-pg")
PGPORT = os.environ.get("PGPORT", "55432")
PGUSER = os.environ.get("PGUSER", "postgres")
DB_NAME = os.environ.get("DB_NAME", "movielens_task")


def scalar(query: str) -> str:
    result = subprocess.run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-Atq",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "-d",
            DB_NAME,
            "-c",
            query,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "build_steps": [
            "base_schema",
            "source_import",
            "catalog_schema",
            "catalog_backfill",
            "catalog_exports",
            "release_shape",
            "release_refresh",
            "release_publish",
        ],
        "movie_rows": int(scalar("SELECT count(*) FROM staging.movies")),
        "genre_rows": int(scalar("SELECT count(*) FROM catalog.genre_dim")),
        "movie_genre_rows": int(scalar("SELECT count(*) FROM catalog.movie_genres")),
        "tag_event_rows": int(scalar("SELECT count(*) FROM catalog.tag_events")),
        "monthly_popularity_rows": int(
            scalar("SELECT count(*) FROM catalog.movie_monthly_popularity")
        ),
        "export_rows": int(scalar("SELECT count(*) FROM catalog.movie_catalog_export")),
    }
    OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
