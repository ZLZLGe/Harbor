---
name: database-migrations-codex
description: Use when delivering a PostgreSQL catalog release through repository migration entrypoints, especially if you need to keep schema and backfill work separated, preserve rollback behavior, and verify rebuilt outputs against current CSV inputs.
---

# Database Migrations Codex Companion

Read `../database-migrations/SKILL.md` first.

## Workflow

1. Start from the repository entrypoints that define the database workflow.
   - `bin/rebuild_db.sh`
   - `bin/migrate_up.sh`
   - `bin/migrate_down.sh`
2. Confirm the staging import layer before touching catalog outputs.
   - All four CSV inputs must load.
   - Rebuild must start from an empty local database.
3. Keep schema creation, data population, and downstream export logic clearly separated.
   - Catalog tables
   - Backfill from staging data
   - Monthly rankings and export view
4. Match the task contract exactly.
   - `Unclassified` is the only mapped genre for `(no genres listed)`
   - `genre_position` preserves the original source order
   - `primary_genre` comes from the first source position
   - `hotness_rank` partitions by calendar month
5. Validate rollback and replay.
   - After `bin/migrate_down.sh`, release objects should be gone
   - Staging imports must remain available
   - Running `bin/migrate_up.sh` again should restore the catalog release
6. Regenerate and verify the report from current inputs.
   - `migration_report.json` should reflect the latest rebuild
   - Alternate input directories should change the rebuilt outputs
