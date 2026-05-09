#!/bin/bash
set -euo pipefail

cp /solution/fixed/migrations/040_catalog_release_schema.up.sql /app/workspace/migrations/040_release_shape.up.sql
cp /solution/fixed/migrations/040_catalog_release_schema.down.sql /app/workspace/migrations/040_release_shape.down.sql
cp /solution/fixed/migrations/050_catalog_release_backfill.up.sql /app/workspace/migrations/050_release_refresh.up.sql
cp /solution/fixed/migrations/050_catalog_release_backfill.down.sql /app/workspace/migrations/050_release_refresh.down.sql
cp /solution/fixed/migrations/060_catalog_release_exports.up.sql /app/workspace/migrations/060_release_publish.up.sql
cp /solution/fixed/migrations/060_catalog_release_exports.down.sql /app/workspace/migrations/060_release_publish.down.sql
cp /solution/fixed/bin/write_report.py /app/workspace/bin/write_report.py
cp /solution/fixed/bin/migrate_down.sh /app/workspace/bin/migrate_down.sh
chmod +x /app/workspace/bin/migrate_down.sh

cd /app/workspace
./bin/rebuild_db.sh
