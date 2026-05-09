CREATE TABLE IF NOT EXISTS catalog.genre_dim (
    genre_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    genre_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS catalog.movie_genres (
    movie_id INTEGER NOT NULL REFERENCES staging.movies(movie_id),
    genre_id INTEGER NOT NULL REFERENCES catalog.genre_dim(genre_id),
    genre_position INTEGER NOT NULL,
    PRIMARY KEY (movie_id, genre_id),
    UNIQUE (movie_id, genre_position)
);

CREATE TABLE IF NOT EXISTS catalog.tag_events (
    tag_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL REFERENCES staging.movies(movie_id),
    tag_text TEXT NOT NULL,
    tagged_at TIMESTAMPTZ NOT NULL,
    UNIQUE (user_id, movie_id, tag_text, tagged_at)
);

CREATE INDEX IF NOT EXISTS idx_catalog_movie_genres_movie
    ON catalog.movie_genres(movie_id, genre_position);

CREATE INDEX IF NOT EXISTS idx_catalog_tag_events_movie_ts
    ON catalog.tag_events(movie_id, tagged_at);
