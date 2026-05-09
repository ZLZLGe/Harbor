import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from io import StringIO
from pathlib import Path

import pandas as pd


WORKSPACE = Path("/app/workspace")
DATA_DIR = WORKSPACE / "data"
OUTPUT_PATH = WORKSPACE / "output" / "migration_report.json"

PGHOST = os.environ.get("PGHOST", "/tmp/database-tools-pg")
PGPORT = os.environ.get("PGPORT", "55432")
PGUSER = os.environ.get("PGUSER", "postgres")
DB_NAME = os.environ.get("DB_NAME", "movielens_task")

EXPECTED_SOURCE_HASHES = {
    "links.csv": "97ad18e4e56a09363c65676b6cb3482ce3e2cea2372a24620c1599c843325f31",
    "movies.csv": "5a5f32dd9bb3797b8e728a1b98958789d2b13f294a69fdfbc5727f8a9611aa07",
    "ratings.csv": "aa289ca83157595d0df6aea1be6a4ded676ddc4385472e8313a8ed9805352646",
    "tags.csv": "92a9f8bb7916dceef6151209845788c3643f794dfa79d1feaec7121b5960399d",
}

EXPECTED_BASELINE_MIGRATION_HASHES = {
    "010_catalog_schema.up.sql": "5c62faf8884ab0606e493837592e177ae0b5999f32249c181274d2dbda22129d",
    "010_catalog_schema.down.sql": "938846bf83e159d199ef066618ac38fb73f2c81b431b9cf822b7afdf8070d003",
    "020_catalog_backfill.up.sql": "2c4e10f741694e4976f71d0ae8d35cfb8c6c6a8fb62e32ce4ecf9135cf87881b",
    "020_catalog_backfill.down.sql": "729c64dba445d3e858895caec67f6609ac032f0f501d6bb3cb631d47c7de5852",
    "030_catalog_exports.up.sql": "45b340998e8b99794ce6997e6b78e1110c8b51566d84581e3bc034df1422cc38",
    "030_catalog_exports.down.sql": "58b18df52c3d28e130df4aa554a4f4b2801f767dce88a341f9866d60acc02352",
}


def run(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, check=True, capture_output=True, text=True, env=merged_env)


def run_shell(command: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return run(["/bin/bash", "-lc", command], env=env)


def psql_scalar(query: str) -> str:
    return run(
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
        ]
    ).stdout.strip()


def psql_rows(query: str) -> list[dict[str, str]]:
    result = run(
        [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            PGHOST,
            "-p",
            PGPORT,
            "-U",
            PGUSER,
            "-d",
            DB_NAME,
            "-c",
            f"COPY ({query}) TO STDOUT WITH CSV HEADER",
        ]
    )
    reader = csv.DictReader(StringIO(result.stdout))
    return list(reader)


def rebuild(env: dict[str, str] | None = None) -> None:
    run_shell("cd /app/workspace && ./bin/rebuild_db.sh", env=env)


def migrate_down() -> None:
    run_shell("cd /app/workspace && ./bin/migrate_down.sh")


def migrate_up() -> None:
    run_shell("cd /app/workspace && ./bin/migrate_up.sh")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(frame: pd.DataFrame) -> str:
    payload = frame.fillna("").to_csv(index=False, lineterminator="\n")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def expand_genres(raw: str) -> list[str]:
    if raw == "(no genres listed)":
        return ["Unclassified"]
    return raw.split("|")


def format_decimal(value: object, places: int = 4) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.{places}f}"


def format_pg_average(sum_value: object, count_value: object, places: int = 4) -> str:
    if pd.isna(sum_value) or pd.isna(count_value) or int(count_value) == 0:
        return ""
    quantizer = Decimal("1").scaleb(-places)
    value = (Decimal(str(sum_value)) / Decimal(int(count_value))).quantize(
        quantizer,
        rounding=ROUND_HALF_UP,
    )
    return f"{value:.{places}f}"


def iso_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@lru_cache(maxsize=None)
def expected_artifacts(data_dir_str: str) -> dict[str, object]:
    data_dir = Path(data_dir_str)

    movies = pd.read_csv(data_dir / "movies.csv").rename(
        columns={"movieId": "movie_id"}
    )
    ratings = pd.read_csv(data_dir / "ratings.csv").rename(
        columns={"userId": "user_id", "movieId": "movie_id", "timestamp": "rated_at_epoch"}
    )
    tags = pd.read_csv(data_dir / "tags.csv").rename(
        columns={"userId": "user_id", "movieId": "movie_id", "tag": "tag_text", "timestamp": "tagged_at_epoch"}
    )
    links = pd.read_csv(
        data_dir / "links.csv",
        dtype={"movieId": "Int64", "imdbId": "string", "tmdbId": "Int64"},
    ).rename(columns={"movieId": "movie_id", "imdbId": "imdb_id", "tmdbId": "tmdb_id"})

    genre_rows: list[tuple[str]] = []
    movie_genre_rows: list[tuple[int, str, int]] = []
    genre_set: set[str] = set()

    for row in movies.itertuples(index=False):
        genres = expand_genres(row.genres)
        for idx, genre_name in enumerate(genres, start=1):
            genre_set.add(genre_name)
            movie_genre_rows.append((int(row.movie_id), genre_name, idx))

    for genre_name in sorted(x for x in genre_set if x != "Unclassified"):
        genre_rows.append((genre_name,))
    if "Unclassified" in genre_set:
        genre_rows.append(("Unclassified",))

    movie_genres_df = pd.DataFrame(
        movie_genre_rows, columns=["movie_id", "genre_name", "genre_position"]
    ).sort_values(["movie_id", "genre_position", "genre_name"], kind="mergesort")

    tag_events_df = tags.copy()
    tag_events_df["tagged_at"] = pd.to_datetime(
        tag_events_df["tagged_at_epoch"], unit="s", utc=True
    )
    tag_events_df = tag_events_df[
        ["user_id", "movie_id", "tag_text", "tagged_at"]
    ].sort_values(["movie_id", "user_id", "tagged_at", "tag_text"], kind="mergesort")
    tag_events_df["tagged_at"] = iso_utc(tag_events_df["tagged_at"])

    ratings["month_start"] = (
        pd.to_datetime(ratings["rated_at_epoch"], unit="s", utc=True)
        .dt.to_period("M")
        .dt.to_timestamp()
        .dt.strftime("%Y-%m-%d")
    )
    tag_months = tags.copy()
    tag_months["month_start"] = (
        pd.to_datetime(tag_months["tagged_at_epoch"], unit="s", utc=True)
        .dt.to_period("M")
        .dt.to_timestamp()
        .dt.strftime("%Y-%m-%d")
    )

    rating_months_df = (
        ratings.groupby(["month_start", "movie_id"], dropna=False)
        .agg(rating_count=("rating", "size"), rating_sum=("rating", "sum"))
        .reset_index()
    )
    tag_months_df = (
        tag_months.groupby(["month_start", "movie_id"], dropna=False)
        .agg(tag_count=("tag_text", "size"))
        .reset_index()
    )
    activity_months_df = pd.concat(
        [
            rating_months_df[["month_start", "movie_id"]],
            tag_months_df[["month_start", "movie_id"]],
        ],
        ignore_index=True,
    ).drop_duplicates(ignore_index=True)
    monthly_df = activity_months_df.merge(
        rating_months_df,
        how="left",
        on=["month_start", "movie_id"],
    ).merge(
        tag_months_df,
        how="left",
        on=["month_start", "movie_id"],
    )
    monthly_df["rating_count"] = monthly_df["rating_count"].fillna(0).astype(int)
    monthly_df["tag_count"] = monthly_df["tag_count"].fillna(0).astype(int)
    monthly_df["avg_rating"] = monthly_df.apply(
        lambda row: ""
        if int(row["rating_count"]) == 0
        else format_pg_average(row["rating_sum"], row["rating_count"]),
        axis=1,
    )
    monthly_df["avg_rating_sort"] = pd.to_numeric(
        monthly_df["avg_rating"], errors="coerce"
    )
    monthly_df = monthly_df.sort_values(
        ["month_start", "rating_count", "avg_rating_sort", "movie_id"],
        ascending=[True, False, False, True],
        kind="mergesort",
        na_position="last",
    )
    monthly_df["hotness_rank"] = monthly_df.groupby("month_start").cumcount() + 1
    monthly_df = monthly_df[
        ["month_start", "movie_id", "rating_count", "avg_rating", "tag_count", "hotness_rank"]
    ].sort_values(["month_start", "hotness_rank", "movie_id"], kind="mergesort")
    monthly_df["rating_count"] = monthly_df["rating_count"].astype(str)
    monthly_df["tag_count"] = monthly_df["tag_count"].astype(str)
    monthly_df["hotness_rank"] = monthly_df["hotness_rank"].astype(str)

    primary_genre_df = movie_genres_df[movie_genres_df["genre_position"] == 1][
        ["movie_id", "genre_name"]
    ].rename(columns={"genre_name": "primary_genre"})
    genre_count_df = (
        movie_genres_df.groupby("movie_id").size().rename("genre_count").reset_index()
    )
    rating_totals_df = (
        ratings.groupby("movie_id")
        .agg(rating_events=("rating", "size"), rating_sum=("rating", "sum"))
        .reset_index()
    )
    rating_totals_df["avg_rating_lifetime"] = rating_totals_df.apply(
        lambda row: format_pg_average(row["rating_sum"], row["rating_events"]),
        axis=1,
    )
    tag_last_df = (
        pd.to_datetime(tags["tagged_at_epoch"], unit="s", utc=True)
        .to_frame(name="tagged_at")
        .join(tags[["movie_id"]])
        .groupby("movie_id")
        .agg(last_tagged_at=("tagged_at", "max"))
        .reset_index()
    )

    export_df = movies.merge(primary_genre_df, how="left", on="movie_id")
    export_df = export_df.merge(genre_count_df, how="left", on="movie_id")
    export_df = export_df.merge(rating_totals_df, how="left", on="movie_id")
    export_df = export_df.merge(tag_last_df, how="left", on="movie_id")
    export_df = export_df.merge(links, how="left", on="movie_id")
    export_df["release_year"] = export_df["title"].str.extract(r"\((\d{4})\)\s*$")[0]
    export_df["genre_count"] = export_df["genre_count"].astype("Int64")
    export_df["rating_events"] = export_df["rating_events"].fillna(0).astype(int)
    export_df["last_tagged_at"] = pd.Series(export_df["last_tagged_at"]).map(
        lambda x: "" if pd.isna(x) else pd.Timestamp(x).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    export_df["tmdb_id"] = export_df["tmdb_id"].map(lambda x: "" if pd.isna(x) else str(int(x)))
    export_df["imdb_id"] = export_df["imdb_id"].fillna("")
    export_df["genre_count"] = export_df["genre_count"].map(lambda x: "" if pd.isna(x) else str(int(x)))
    export_df["rating_events"] = export_df["rating_events"].astype(str)
    export_df["release_year"] = export_df["release_year"].fillna("")
    export_df = export_df[
        [
            "movie_id",
            "title",
            "release_year",
            "primary_genre",
            "genre_count",
            "rating_events",
            "avg_rating_lifetime",
            "last_tagged_at",
            "imdb_id",
            "tmdb_id",
        ]
    ].sort_values(["movie_id"], kind="mergesort")
    export_df["movie_id"] = export_df["movie_id"].astype(str)

    genre_df = pd.DataFrame(genre_rows, columns=["genre_name"])
    movie_genres_df = movie_genres_df.astype(
        {"movie_id": str, "genre_position": str}
    )
    tag_events_df["user_id"] = tag_events_df["user_id"].astype(str)
    tag_events_df["movie_id"] = tag_events_df["movie_id"].astype(str)

    return {
        "movie_rows": len(movies),
        "genre_rows": len(genre_df),
        "movie_genre_rows": len(movie_genres_df),
        "tag_event_rows": len(tag_events_df),
        "monthly_popularity_rows": len(monthly_df),
        "export_rows": len(export_df),
        "genres": genre_df,
        "movie_genres": movie_genres_df,
        "tag_events": tag_events_df,
        "monthly": monthly_df.astype({"movie_id": str}),
        "export": export_df,
        "genre_hash": stable_hash(genre_df),
        "movie_genre_hash": stable_hash(movie_genres_df),
        "tag_event_hash": stable_hash(tag_events_df),
        "monthly_hash": stable_hash(monthly_df.astype({"movie_id": str})),
        "export_hash": stable_hash(export_df),
    }


def actual_genres_df() -> pd.DataFrame:
    rows = psql_rows(
        """
        SELECT genre_name
        FROM catalog.genre_dim
        ORDER BY
            CASE WHEN genre_name = 'Unclassified' THEN 1 ELSE 0 END,
            genre_name
        """
    )
    return pd.DataFrame(rows, columns=["genre_name"])


def actual_movie_genres_df() -> pd.DataFrame:
    rows = psql_rows(
        """
        SELECT
            mg.movie_id::text AS movie_id,
            gd.genre_name,
            mg.genre_position::text AS genre_position
        FROM catalog.movie_genres AS mg
        JOIN catalog.genre_dim AS gd
            ON gd.genre_id = mg.genre_id
        ORDER BY mg.movie_id, mg.genre_position, gd.genre_name
        """
    )
    return pd.DataFrame(rows, columns=["movie_id", "genre_name", "genre_position"])


def actual_tag_events_df() -> pd.DataFrame:
    rows = psql_rows(
        """
        SELECT
            user_id::text AS user_id,
            movie_id::text AS movie_id,
            tag_text,
            to_char(tagged_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS tagged_at
        FROM catalog.tag_events
        ORDER BY catalog.tag_events.movie_id, catalog.tag_events.user_id, catalog.tag_events.tagged_at, catalog.tag_events.tag_text
        """
    )
    return pd.DataFrame(rows, columns=["user_id", "movie_id", "tag_text", "tagged_at"])


def actual_monthly_df() -> pd.DataFrame:
    rows = psql_rows(
        """
        SELECT
            to_char(month_start, 'YYYY-MM-DD') AS month_start,
            movie_id::text AS movie_id,
            rating_count::text AS rating_count,
            to_char(avg_rating, 'FM999999990.0000') AS avg_rating,
            tag_count::text AS tag_count,
            hotness_rank::text AS hotness_rank
        FROM catalog.movie_monthly_popularity
        ORDER BY catalog.movie_monthly_popularity.month_start, catalog.movie_monthly_popularity.hotness_rank, catalog.movie_monthly_popularity.movie_id
        """
    )
    return pd.DataFrame(
        rows,
        columns=["month_start", "movie_id", "rating_count", "avg_rating", "tag_count", "hotness_rank"],
    )


def actual_export_df() -> pd.DataFrame:
    rows = psql_rows(
        """
        SELECT
            movie_id::text AS movie_id,
            title,
            COALESCE(release_year::text, '') AS release_year,
            COALESCE(primary_genre, '') AS primary_genre,
            COALESCE(genre_count::text, '') AS genre_count,
            rating_events::text AS rating_events,
            COALESCE(to_char(avg_rating_lifetime, 'FM999999990.0000'), '') AS avg_rating_lifetime,
            COALESCE(to_char(last_tagged_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '') AS last_tagged_at,
            COALESCE(imdb_id, '') AS imdb_id,
            COALESCE(tmdb_id::text, '') AS tmdb_id
        FROM catalog.movie_catalog_export
        ORDER BY catalog.movie_catalog_export.movie_id
        """
    )
    return pd.DataFrame(
        rows,
        columns=[
            "movie_id",
            "title",
            "release_year",
            "primary_genre",
            "genre_count",
            "rating_events",
            "avg_rating_lifetime",
            "last_tagged_at",
            "imdb_id",
            "tmdb_id",
        ],
    )


def assert_source_hashes_unchanged() -> None:
    for filename, expected_hash in EXPECTED_SOURCE_HASHES.items():
        assert file_sha256(DATA_DIR / filename) == expected_hash


def assert_baseline_migration_hashes_unchanged() -> None:
    migrations_dir = WORKSPACE / "migrations"
    for filename, expected_hash in EXPECTED_BASELINE_MIGRATION_HASHES.items():
        assert file_sha256(migrations_dir / filename) == expected_hash


def test_rebuild_and_report_contract() -> None:
    assert_source_hashes_unchanged()
    assert_baseline_migration_hashes_unchanged()
    rebuild()

    assert OUTPUT_PATH.is_file(), "migration_report.json was not created"
    report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    expected = expected_artifacts(str(DATA_DIR))

    assert report["build_steps"] == [
        "base_schema",
        "source_import",
        "catalog_schema",
        "catalog_backfill",
        "catalog_exports",
        "release_shape",
        "release_refresh",
        "release_publish",
    ]
    assert report["movie_rows"] == expected["movie_rows"]
    assert report["genre_rows"] == expected["genre_rows"]
    assert report["movie_genre_rows"] == expected["movie_genre_rows"]
    assert report["tag_event_rows"] == expected["tag_event_rows"]
    assert report["monthly_popularity_rows"] == expected["monthly_popularity_rows"]
    assert report["export_rows"] == expected["export_rows"]

    versions = psql_rows(
        """
        SELECT version
        FROM meta.schema_migrations
        ORDER BY version
        """
    )
    assert [row["version"] for row in versions] == [
        "000_base_staging_schema",
        "010_catalog_schema",
        "020_catalog_backfill",
        "030_catalog_exports",
        "040_release_shape",
        "050_release_refresh",
        "060_release_publish",
    ]


def test_catalog_tables_match_expected_content() -> None:
    expected = expected_artifacts(str(DATA_DIR))

    actual_genres = actual_genres_df()
    assert stable_hash(actual_genres) == expected["genre_hash"]

    actual_movie_genres = actual_movie_genres_df()
    assert stable_hash(actual_movie_genres) == expected["movie_genre_hash"]

    actual_tag_events = actual_tag_events_df()
    assert stable_hash(actual_tag_events) == expected["tag_event_hash"]


def test_monthly_popularity_and_export_match_expected_content() -> None:
    expected = expected_artifacts(str(DATA_DIR))

    actual_monthly = actual_monthly_df()
    assert stable_hash(actual_monthly) == expected["monthly_hash"]

    actual_export = actual_export_df()
    assert stable_hash(actual_export) == expected["export_hash"]


def test_migrate_down_and_reapply_release() -> None:
    migrate_down()

    assert psql_scalar("SELECT to_regclass('staging.movies') IS NOT NULL") == "t"
    assert psql_scalar("SELECT count(*) FROM staging.movies") == str(expected_artifacts(str(DATA_DIR))["movie_rows"])
    assert psql_scalar("SELECT to_regclass('catalog.genre_dim') IS NULL") == "t"
    assert psql_scalar("SELECT to_regclass('catalog.movie_genres') IS NULL") == "t"
    assert psql_scalar("SELECT to_regclass('catalog.tag_events') IS NULL") == "t"
    assert psql_scalar("SELECT to_regclass('catalog.movie_monthly_popularity') IS NULL") == "t"
    assert psql_scalar("SELECT to_regclass('catalog.movie_catalog_export') IS NULL") == "t"

    versions_after_down = psql_rows(
        """
        SELECT version
        FROM meta.schema_migrations
        ORDER BY version
        """
    )
    assert [row["version"] for row in versions_after_down] == ["000_base_staging_schema"]

    migrate_up()

    actual_monthly = actual_monthly_df()
    actual_export = actual_export_df()
    expected = expected_artifacts(str(DATA_DIR))

    assert stable_hash(actual_monthly) == expected["monthly_hash"]
    assert stable_hash(actual_export) == expected["export_hash"]


def test_rebuild_uses_current_input_directory() -> None:
    with tempfile.TemporaryDirectory(prefix="movielens-alt-") as tmp:
        alt_dir = Path(tmp)
        for filename in ["movies.csv", "ratings.csv", "tags.csv", "links.csv"]:
            shutil.copy2(DATA_DIR / filename, alt_dir / filename)

        for filename, line in [
            ("movies.csv", '999999,Verifier Synthetic Feature (2018),(no genres listed)\n'),
            ("ratings.csv", "999999,999999,4.5,1512086400\n"),
            ("tags.csv", "999999,999999,verifier-sandbox,1512086400\n"),
            ("links.csv", "999999,1234567,7654321\n"),
        ]:
            path = alt_dir / filename
            payload = path.read_text(encoding="utf-8")
            if not payload.endswith("\n"):
                payload += "\n"
            payload += line
            path.write_text(payload, encoding="utf-8")

        rebuild(env={"MOVIELENS_DATA_DIR": str(alt_dir)})
        expected_alt = expected_artifacts(str(alt_dir))
        report = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

        assert report["movie_rows"] == expected_alt["movie_rows"]
        assert report["genre_rows"] == expected_alt["genre_rows"]
        assert report["movie_genre_rows"] == expected_alt["movie_genre_rows"]
        assert report["tag_event_rows"] == expected_alt["tag_event_rows"]
        assert report["monthly_popularity_rows"] == expected_alt["monthly_popularity_rows"]
        assert report["export_rows"] == expected_alt["export_rows"]

        export_rows = psql_rows(
            """
            SELECT
                movie_id::text AS movie_id,
                primary_genre,
                genre_count::text AS genre_count,
                rating_events::text AS rating_events,
                COALESCE(to_char(last_tagged_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'), '') AS last_tagged_at,
                COALESCE(imdb_id, '') AS imdb_id,
                COALESCE(tmdb_id::text, '') AS tmdb_id
            FROM catalog.movie_catalog_export
            WHERE movie_id = 999999
            """
        )
        assert export_rows == [
            {
                "movie_id": "999999",
                "primary_genre": "Unclassified",
                "genre_count": "1",
                "rating_events": "1",
                "last_tagged_at": "2017-12-01T00:00:00Z",
                "imdb_id": "1234567",
                "tmdb_id": "7654321",
            }
        ]

        monthly_rows = psql_rows(
            """
            SELECT
                to_char(month_start, 'YYYY-MM-DD') AS month_start,
                rating_count::text AS rating_count,
                tag_count::text AS tag_count
            FROM catalog.movie_monthly_popularity
            WHERE movie_id = 999999
            """
        )
        assert monthly_rows == [
            {
                "month_start": "2017-12-01",
                "rating_count": "1",
                "tag_count": "1",
            }
        ]
