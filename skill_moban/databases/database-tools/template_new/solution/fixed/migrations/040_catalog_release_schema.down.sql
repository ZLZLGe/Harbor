ALTER TABLE IF EXISTS catalog.movie_monthly_popularity
    ALTER COLUMN avg_rating SET NOT NULL;
