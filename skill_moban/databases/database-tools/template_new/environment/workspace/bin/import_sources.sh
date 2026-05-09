#!/usr/bin/env bash

set -euo pipefail

source /app/workspace/bin/common.sh
/app/workspace/bin/start_postgres.sh >/dev/null

for file in movies.csv ratings.csv tags.csv links.csv; do
    if [ ! -f "$DATA_DIR/$file" ]; then
        echo "Missing source file: $DATA_DIR/$file" >&2
        exit 1
    fi
done

psql_db <<'SQL'
TRUNCATE TABLE staging.movies;
TRUNCATE TABLE staging.ratings;
TRUNCATE TABLE staging.tags;
TRUNCATE TABLE staging.links;
SQL

psql_db -c "\copy staging.movies(movie_id, title, genres) FROM '$DATA_DIR/movies.csv' CSV HEADER"
psql_db -c "\copy staging.ratings(user_id, movie_id, rating, rated_at_epoch) FROM '$DATA_DIR/ratings.csv' CSV HEADER"
psql_db -c "\copy staging.tags(user_id, movie_id, tag_text, tagged_at_epoch) FROM '$DATA_DIR/tags.csv' CSV HEADER"
psql_db -c "\copy staging.links(movie_id, imdb_id, tmdb_id) FROM '$DATA_DIR/links.csv' CSV HEADER"
