DROP INDEX IF EXISTS idx_catalog_tag_events_movie_ts;
DROP INDEX IF EXISTS idx_catalog_movie_genres_movie;

DROP VIEW IF EXISTS catalog.movie_catalog_export;
DROP TABLE IF EXISTS catalog.movie_monthly_popularity;
DROP TABLE IF EXISTS catalog.tag_events;
DROP TABLE IF EXISTS catalog.movie_genres;
DROP TABLE IF EXISTS catalog.genre_dim;
