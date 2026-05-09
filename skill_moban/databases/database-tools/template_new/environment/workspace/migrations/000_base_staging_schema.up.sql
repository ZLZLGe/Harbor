CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS catalog;
CREATE SCHEMA IF NOT EXISTS meta;

CREATE TABLE IF NOT EXISTS staging.movies (
    movie_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    genres TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.ratings (
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    rating NUMERIC(2,1) NOT NULL,
    rated_at_epoch BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.tags (
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    tag_text TEXT NOT NULL,
    tagged_at_epoch BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.links (
    movie_id INTEGER PRIMARY KEY,
    imdb_id TEXT,
    tmdb_id INTEGER
);
