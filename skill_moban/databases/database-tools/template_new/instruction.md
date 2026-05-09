You are preparing an updated PostgreSQL catalog release in `/app/workspace/`. The repository already uses versioned migrations, and the current rebuild entrypoints and staging import flow must stay in place.

Input data is in `/app/workspace/data/`:
- `movies.csv`: movie identifiers, titles, and pipe-delimited genre strings
- `ratings.csv`: user ratings with epoch-second timestamps
- `tags.csv`: user tags with epoch-second timestamps
- `links.csv`: IMDb and TMDb identifier mappings

The provided database workflow is in `/app/workspace/`:
- `bin/rebuild_db.sh`: rebuilds the database from scratch; keep this path and filename
- `bin/migrate_up.sh`: applies the repository's current database changes
- `bin/migrate_down.sh`: rolls back the updated catalog release while keeping the staging imports available
- `migrations/`
- `sql/`

Your tasks
1. Keep the existing PostgreSQL rebuild flow so `bin/rebuild_db.sh` still rebuilds staging from the four CSV files and then materializes the catalog through the repository migration entrypoints.
2. After the rebuild finishes, the database must provide and keep these objects queryable:
   - Table `catalog.genre_dim`
   - Table `catalog.movie_genres`
   - Table `catalog.tag_events`
   - Table `catalog.movie_monthly_popularity`
   - View `catalog.movie_catalog_export`
   - File `/app/workspace/output/migration_report.json`
3. Satisfy these business definitions for the final rebuilt release:
   - All four input files must participate in the rebuilt catalog.
   - `genre_dim` must contain one row per distinct genre label from `movies.csv`, plus exactly one `Unclassified` row for titles whose genre value is `(no genres listed)`.
   - `movie_genres` must contain one row per `(movie_id, genre_id)` mapping. Every movie must have at least one mapping. Titles with `(no genres listed)` must map only to `Unclassified`.
   - `movie_genres.genre_position` must preserve the original left-to-right order from the source `genres` string.
   - `tag_events` must preserve `user_id`, `movie_id`, `tag_text`, and `tagged_at`, where `tagged_at` is the UTC timestamp converted from the source epoch seconds.
   - `movie_monthly_popularity` must contain one row for every `(month_start, movie_id)` bucket that has ratings or tags in that calendar month.
   - In `movie_monthly_popularity`, `rating_count` is the number of ratings for that movie-month bucket, `tag_count` is the number of tags for that movie-month bucket, and `avg_rating` is null when that movie-month has tags but no ratings.
   - `movie_monthly_popularity.hotness_rank` must rank rows within each month by highest `rating_count`, then highest `avg_rating`, then lowest `movie_id`.
   - `movie_catalog_export` must return one row per movie and include at least `movie_id`, `title`, `release_year`, `primary_genre`, `genre_count`, `rating_events`, `avg_rating_lifetime`, `last_tagged_at`, `imdb_id`, and `tmdb_id`.
   - In `movie_catalog_export`, `primary_genre` must come from the first position in the source genre sequence. For titles with `(no genres listed)`, it must be `Unclassified`.
   - In `movie_catalog_export`, `release_year` must be parsed from a trailing `(YYYY)` suffix in the title when present; otherwise it must be null.
4. Regenerate `/app/workspace/output/migration_report.json` from the rebuilt database, and set `build_steps` to this exact ordered list:
   - `base_schema`
   - `source_import`
   - `catalog_schema`
   - `catalog_backfill`
   - `catalog_exports`
   - `release_shape`
   - `release_refresh`
   - `release_publish`
5. `bin/migrate_down.sh` must remove the updated catalog release while leaving the current staged inputs available, and `bin/migrate_up.sh` must restore the rebuilt catalog from the current CSV inputs.

Output
- Database changes under the existing repository layout.
- `/app/workspace/output/migration_report.json` must be valid UTF-8 JSON and include at least:
  - `build_steps`
  - `movie_rows`
  - `genre_rows`
  - `movie_genre_rows`
  - `tag_event_rows`
  - `monthly_popularity_rows`
  - `export_rows`
- After `bin/rebuild_db.sh` completes, the required tables and view above must be directly queryable, and `migration_report.json` must be regenerated from the current CSV inputs.

Notes
- Do not modify the input CSV files to satisfy the checks.
- Do not replace PostgreSQL, bypass the repository migration entrypoints, or swap the task into a one-off script that only writes the final JSON file.
- Do not hard-code expected counts, rankings, or export rows, and do not store precomputed answers in seed files.
- Do not evade the work by removing the rollback path, keeping only a cached report file, or relying on one-off output generation that skips the database rebuild flow.
- You may add SQL, migration files, helper scripts, and supporting database objects, but preserve the existing entrypoint paths and deliverable names.
