-- queries.sql : 7 business queries for Movie Ratings and Box-Office Analysis
-- Written for SQLite (tested). Oracle changes are noted in the comments.
-- Rules used in every query:
--   * rating averages use reliable_rating = 1 (rating exists and votes >= 10)
--   * revenue / profit averages ignore NULLs (0 and bad values were set to NULL in cleaning)
--   * a movie with several genres is counted once in EACH genre, so genre rows overlap

-- Q1 Overall KPIs (BQ: how big is the data we can trust?)
SELECT COUNT(*)                                                    AS movies,
       SUM(CASE WHEN revenue_usd IS NOT NULL THEN 1 ELSE 0 END)    AS movies_with_revenue,
       SUM(CASE WHEN profit_usd  IS NOT NULL THEN 1 ELSE 0 END)    AS movies_with_profit,
       ROUND(AVG(CASE WHEN reliable_rating = 1 THEN rating END), 2) AS avg_rating,
       ROUND(AVG(revenue_usd), 0)                                  AS avg_revenue_usd,
       ROUND(AVG(profit_usd), 0)                                   AS avg_profit_usd
FROM fact_movie_performance;

-- Q2 BQ1: average rating and average revenue by genre
SELECT g.genre_name,
       COUNT(DISTINCT CASE WHEN f.reliable_rating = 1 THEN f.movie_id END) AS movies_rated,
       ROUND(AVG(CASE WHEN f.reliable_rating = 1 THEN f.rating END), 2)    AS avg_rating,
       COUNT(f.revenue_usd)                                                AS movies_with_revenue,
       ROUND(AVG(f.revenue_usd), 0)                                        AS avg_revenue_usd
FROM fact_movie_performance f
JOIN bridge_movie_genre b ON b.movie_id = f.movie_id
JOIN dim_genre g          ON g.genre_key = b.genre_key
GROUP BY g.genre_name
ORDER BY avg_revenue_usd DESC;

-- Q3 BQ2: do higher-rated movies earn more? (rating bands)
SELECT CASE WHEN rating < 5 THEN '1) below 5'
            WHEN rating < 6 THEN '2) 5 to 5.9'
            WHEN rating < 7 THEN '3) 6 to 6.9'
            WHEN rating < 8 THEN '4) 7 to 7.9'
            ELSE                 '5) 8 and above' END AS rating_band,
       COUNT(*)                          AS movies,
       ROUND(AVG(revenue_usd), 0)        AS avg_revenue_usd,
       ROUND(AVG(profit_usd), 0)         AS avg_profit_usd
FROM fact_movie_performance
WHERE reliable_rating = 1 AND revenue_usd IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- Q4 BQ3: top 10 movies by profit
-- Oracle: replace LIMIT 10 with FETCH FIRST 10 ROWS ONLY
SELECT m.title, d.year AS release_year, f.budget_usd, f.revenue_usd, f.profit_usd, f.rating
FROM fact_movie_performance f
JOIN dim_movie m ON m.movie_id = f.movie_id
JOIN dim_date  d ON d.date_key = f.release_date_key
WHERE f.profit_usd IS NOT NULL
ORDER BY f.profit_usd DESC
LIMIT 10;

-- Q5 BQ4: does a bigger budget mean more profit? (budget bands)
SELECT CASE WHEN budget_usd <   1000000 THEN '1) under 1M'
            WHEN budget_usd <  10000000 THEN '2) 1M to 10M'
            WHEN budget_usd <  50000000 THEN '3) 10M to 50M'
            WHEN budget_usd < 100000000 THEN '4) 50M to 100M'
            ELSE                             '5) 100M and above' END AS budget_band,
       COUNT(*)                                   AS movies,
       ROUND(AVG(profit_usd), 0)                  AS avg_profit_usd,
       ROUND(AVG(roi), 2)                         AS avg_roi,
       ROUND(100.0 * SUM(CASE WHEN profit_usd > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_profitable
FROM fact_movie_performance
WHERE profit_usd IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- Q6 BQ5: yearly trend with year-over-year revenue growth
-- Window function LAG: works on Oracle and on SQLite 3.25 or newer.
-- 2017 is left out because the source data is incomplete for that year.
WITH y AS (
    SELECT d.year,
           COUNT(*)                                                     AS movies,
           ROUND(AVG(CASE WHEN f.reliable_rating = 1 THEN f.rating END), 2) AS avg_rating,
           SUM(f.revenue_usd)                                           AS total_revenue_usd
    FROM fact_movie_performance f
    JOIN dim_date d ON d.date_key = f.release_date_key
    WHERE d.year BETWEEN 1990 AND 2016
    GROUP BY d.year
)
SELECT year, movies, avg_rating, total_revenue_usd,
       ROUND(100.0 * (total_revenue_usd - LAG(total_revenue_usd) OVER (ORDER BY year))
             / LAG(total_revenue_usd) OVER (ORDER BY year), 1) AS revenue_growth_pct
FROM y
ORDER BY year;

-- Q7 Best release months (average revenue per movie)
-- Oracle: month and month_name come from dim_date, so no date function change is needed.
SELECT d.month, d.month_name,
       COUNT(f.revenue_usd)            AS movies_with_revenue,
       ROUND(AVG(f.revenue_usd), 0)    AS avg_revenue_usd
FROM fact_movie_performance f
JOIN dim_date d ON d.date_key = f.release_date_key
WHERE d.month IS NOT NULL
GROUP BY d.month, d.month_name
ORDER BY avg_revenue_usd DESC;
