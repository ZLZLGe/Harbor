TRUNCATE TABLE catalog.movie_genres;
TRUNCATE TABLE catalog.tag_events RESTART IDENTITY;
TRUNCATE TABLE catalog.genre_dim RESTART IDENTITY CASCADE;

INSERT INTO catalog.genre_dim (genre_name)
SELECT genre_name
FROM (
    SELECT DISTINCT
        CASE
            WHEN movies.genres = '(no genres listed)' THEN 'Unclassified'
            ELSE genre_entry.genre_name
        END AS genre_name
    FROM staging.movies AS movies
    LEFT JOIN LATERAL regexp_split_to_table(movies.genres, '\|') AS genre_entry(genre_name)
        ON movies.genres <> '(no genres listed)'
) AS distinct_genres
ORDER BY genre_name;

INSERT INTO catalog.movie_genres (movie_id, genre_id, genre_position)
SELECT
    source_rows.movie_id,
    genre_dim.genre_id,
    source_rows.genre_position
FROM (
    SELECT
        movies.movie_id,
        CASE
            WHEN movies.genres = '(no genres listed)' THEN 'Unclassified'
            ELSE genre_entry.genre_name
        END AS genre_name,
        CASE
            WHEN movies.genres = '(no genres listed)' THEN 1
            ELSE genre_entry.genre_position
        END AS genre_position
    FROM staging.movies AS movies
    LEFT JOIN LATERAL regexp_split_to_table(movies.genres, '\|') WITH ORDINALITY AS genre_entry(genre_name, genre_position)
        ON movies.genres <> '(no genres listed)'
) AS source_rows
JOIN catalog.genre_dim AS genre_dim
    ON genre_dim.genre_name = source_rows.genre_name
ORDER BY source_rows.movie_id, source_rows.genre_position;

INSERT INTO catalog.tag_events (user_id, movie_id, tag_text, tagged_at)
SELECT
    user_id,
    movie_id,
    tag_text,
    TIMESTAMPTZ 'epoch' + (tagged_at_epoch * INTERVAL '1 second')
FROM staging.tags
ORDER BY user_id, movie_id, tag_text, tagged_at_epoch;
