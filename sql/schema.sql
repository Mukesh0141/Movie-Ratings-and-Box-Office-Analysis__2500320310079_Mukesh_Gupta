-- Star schema for Movie Ratings and Box-Office Analysis (SQLite)
-- Grain of the fact table: ONE ROW PER MOVIE.
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS bridge_movie_genre;
DROP TABLE IF EXISTS fact_movie_performance;
DROP TABLE IF EXISTS dim_genre;
DROP TABLE IF EXISTS dim_language;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_movie;

-- ---------------------------------------------------------------- dimensions
CREATE TABLE dim_movie (
    movie_id      INTEGER PRIMARY KEY,                  -- TMDB id from the raw file
    title         TEXT    NOT NULL CHECK (length(trim(title)) > 0)
);

CREATE TABLE dim_date (
    date_key      INTEGER PRIMARY KEY,                  -- YYYYMMDD, 0 = unknown date
    full_date     TEXT,                                 -- 'YYYY-MM-DD', NULL for unknown
    year          INTEGER CHECK (year BETWEEN 1870 AND 2030),
    quarter       INTEGER CHECK (quarter BETWEEN 1 AND 4),
    month         INTEGER CHECK (month BETWEEN 1 AND 12),
    month_name    TEXT,
    day_of_month  INTEGER CHECK (day_of_month BETWEEN 1 AND 31),
    CHECK ((date_key = 0 AND full_date IS NULL) OR (date_key > 0 AND full_date IS NOT NULL))
);

CREATE TABLE dim_language (
    language_key  INTEGER PRIMARY KEY,
    language_code TEXT NOT NULL UNIQUE CHECK (length(language_code) BETWEEN 2 AND 7)  -- 'en', 'unknown'
);

CREATE TABLE dim_genre (
    genre_key     INTEGER PRIMARY KEY,
    genre_name    TEXT NOT NULL UNIQUE CHECK (length(trim(genre_name)) > 0)
);

-- ---------------------------------------------------------------- fact
CREATE TABLE fact_movie_performance (
    movie_id         INTEGER PRIMARY KEY,               -- PK = FK, because grain = one row per movie
    release_date_key INTEGER NOT NULL DEFAULT 0,
    language_key     INTEGER NOT NULL,
    runtime_min      INTEGER CHECK (runtime_min IS NULL OR runtime_min > 0),
    budget_usd       INTEGER CHECK (budget_usd  IS NULL OR budget_usd  >= 1000),
    revenue_usd      INTEGER CHECK (revenue_usd IS NULL OR revenue_usd >= 1000),
    profit_usd       INTEGER,
    roi              REAL    CHECK (roi IS NULL OR roi >= 0),
    rating           REAL    CHECK (rating IS NULL OR rating BETWEEN 0 AND 10),
    votes            INTEGER NOT NULL DEFAULT 0 CHECK (votes >= 0),
    reliable_rating  INTEGER NOT NULL DEFAULT 0 CHECK (reliable_rating IN (0, 1)),
    FOREIGN KEY (movie_id)         REFERENCES dim_movie(movie_id),
    FOREIGN KEY (release_date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (language_key)     REFERENCES dim_language(language_key),
    -- profit and ROI exist only when budget and revenue both exist
    CHECK ((profit_usd IS NULL AND roi IS NULL)
        OR (budget_usd IS NOT NULL AND revenue_usd IS NOT NULL
            AND profit_usd = revenue_usd - budget_usd)),
    -- a reliable rating needs a rating and at least 10 votes
    CHECK (reliable_rating = 0 OR (rating IS NOT NULL AND votes >= 10))
);

-- ---------------------------------------------------------------- bridge (many movies <-> many genres)
CREATE TABLE bridge_movie_genre (
    movie_id   INTEGER NOT NULL,
    genre_key  INTEGER NOT NULL,
    PRIMARY KEY (movie_id, genre_key),
    FOREIGN KEY (movie_id)  REFERENCES fact_movie_performance(movie_id),
    FOREIGN KEY (genre_key) REFERENCES dim_genre(genre_key)
);

-- helpful indexes for joins and filters
CREATE INDEX ix_fact_date     ON fact_movie_performance(release_date_key);
CREATE INDEX ix_fact_language ON fact_movie_performance(language_key);
CREATE INDEX ix_bridge_genre  ON bridge_movie_genre(genre_key);

-- unknown-date member, so every movie can have a valid date key
INSERT INTO dim_date (date_key, full_date, year, quarter, month, month_name, day_of_month)
VALUES (0, NULL, NULL, NULL, NULL, 'Unknown', NULL);
