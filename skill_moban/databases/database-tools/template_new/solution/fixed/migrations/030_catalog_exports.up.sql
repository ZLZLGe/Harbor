DROP VIEW IF EXISTS catalog.movie_catalog_export;
DROP TABLE IF EXISTS catalog.movie_monthly_popularity;

CREATE TABLE catalog.movie_monthly_popularity (
    month_start DATE NOT NULL,
    movie_id INTEGER NOT NULL REFERENCES staging.movies(movie_id),
    rating_count INTEGER NOT NULL,
    avg_rating NUMERIC(6,4) NOT NULL,
    tag_count INTEGER NOT NULL,
    hotness_rank INTEGER NOT NULL,
    PRIMARY KEY (month_start, movie_id)
);

INSERT INTO catalog.movie_monthly_popularity (
    month_start,
    movie_id,
    rating_count,
    avg_rating,
    tag_count,
    hotness_rank
)
WITH rating_months AS (
    SELECT
        date_trunc('month', timezone('UTC', to_timestamp(rated_at_epoch)))::date AS month_start,
        movie_id,
        count(*)::integer AS rating_count,
        round(avg(rating)::numeric, 4) AS avg_rating
    FROM staging.ratings
    GROUP BY 1, 2
),
tag_months AS (
    SELECT
        date_trunc('month', tagged_at)::date AS month_start,
        movie_id,
        count(*)::integer AS tag_count
    FROM catalog.tag_events
    GROUP BY 1, 2
),
scored AS (
    SELECT
        rating_months.month_start,
        rating_months.movie_id,
        rating_months.rating_count,
        rating_months.avg_rating,
        COALESCE(tag_months.tag_count, 0) AS tag_count,
        row_number() OVER (
            PARTITION BY rating_months.month_start
            ORDER BY
                rating_months.rating_count DESC,
                rating_months.avg_rating DESC,
                rating_months.movie_id ASC
        )::integer AS hotness_rank
    FROM rating_months
    LEFT JOIN tag_months
        ON tag_months.month_start = rating_months.month_start
       AND tag_months.movie_id = rating_months.movie_id
)
SELECT
    month_start,
    movie_id,
    rating_count,
    avg_rating,
    tag_count,
    hotness_rank
FROM scored;

CREATE VIEW catalog.movie_catalog_export AS
WITH rating_totals AS (
    SELECT
        movie_id,
        count(*)::integer AS rating_events,
        round(avg(rating)::numeric, 4) AS avg_rating_lifetime
    FROM staging.ratings
    GROUP BY movie_id
),
tag_totals AS (
    SELECT
        movie_id,
        max(tagged_at) AS last_tagged_at
    FROM catalog.tag_events
    GROUP BY movie_id
),
primary_genres AS (
    SELECT
        movie_genres.movie_id,
        genre_dim.genre_name AS primary_genre
    FROM catalog.movie_genres AS movie_genres
    JOIN catalog.genre_dim AS genre_dim
        ON genre_dim.genre_id = movie_genres.genre_id
    WHERE movie_genres.genre_position = 1
),
genre_counts AS (
    SELECT
        movie_id,
        count(*)::integer AS genre_count
    FROM catalog.movie_genres
    GROUP BY movie_id
)
SELECT
    movies.movie_id,
    movies.title,
    substring(movies.title from '\(([0-9]{4})\)\s*$')::integer AS release_year,
    primary_genres.primary_genre,
    genre_counts.genre_count,
    COALESCE(rating_totals.rating_events, 0) AS rating_events,
    rating_totals.avg_rating_lifetime,
    tag_totals.last_tagged_at,
    links.imdb_id,
    links.tmdb_id
FROM staging.movies AS movies
LEFT JOIN primary_genres
    ON primary_genres.movie_id = movies.movie_id
LEFT JOIN genre_counts
    ON genre_counts.movie_id = movies.movie_id
LEFT JOIN rating_totals
    ON rating_totals.movie_id = movies.movie_id
LEFT JOIN tag_totals
    ON tag_totals.movie_id = movies.movie_id
LEFT JOIN staging.links AS links
    ON links.movie_id = movies.movie_id;
